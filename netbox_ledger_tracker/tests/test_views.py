from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from netbox_ledger_tracker.models import Currency, Expense, ExpensePart, Ledger, Person
from netbox_ledger_tracker.views import (
    CurrencyListView,
    ExpenseListView,
    ExpenseSplitView,
    LedgerListView,
    LedgerSettleUpView,
    PersonListView,
)

User = get_user_model()


class ListViewSmokeTest(TestCase):
    """Every model's list view should render for a superuser without error."""

    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = User.objects.create_user(username='ledger-admin', password='pass', is_superuser=True)
        self.currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        self.ledger = Ledger.objects.create(name='Summer trip', currency=self.currency)
        Person.objects.create(name='Alice', ledger=self.ledger)

    def _get(self, view_cls, path):
        request = self.factory.get(path)
        request.user = self.superuser
        response = view_cls.as_view()(request)
        response.render()
        return response

    def test_currency_list(self):
        self.assertEqual(self._get(CurrencyListView, '/plugins/ledger/currencies/').status_code, 200)

    def test_ledger_list(self):
        self.assertEqual(self._get(LedgerListView, '/plugins/ledger/ledgers/').status_code, 200)

    def test_person_list(self):
        self.assertEqual(self._get(PersonListView, '/plugins/ledger/people/').status_code, 200)

    def test_expense_list(self):
        self.assertEqual(self._get(ExpenseListView, '/plugins/ledger/expenses/').status_code, 200)


class ExpenseSplitViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = User.objects.create_user(username='split-admin', password='pass', is_superuser=True)
        self.currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        self.ledger = Ledger.objects.create(name='Summer trip', currency=self.currency)
        self.alice = Person.objects.create(name='Alice', ledger=self.ledger)
        self.bob = Person.objects.create(name='Bob', ledger=self.ledger)

    def _post_data(self, **overrides):
        data = {
            'name': 'Dinner',
            'ledger': self.ledger.pk,
            'currency': self.currency.pk,
            'amount': '100',
            'date': '2026-01-01',
            'comments': '',
            f'person-involved-{self.alice.pk}': 'on',
            f'person-haspaid-{self.alice.pk}': '100',
            f'person-auto-{self.alice.pk}': 'on',
            f'person-involved-{self.bob.pk}': 'on',
            f'person-haspaid-{self.bob.pk}': '0',
            f'person-auto-{self.bob.pk}': 'on',
        }
        data.update(overrides)
        return data

    def test_get_without_ledger_shows_picker(self):
        request = self.factory.get('/plugins/ledger/expenses/split/add/')
        request.user = self.superuser

        response = ExpenseSplitView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pick which ledger', response.content)

    def test_get_with_ledger_shows_person_fields(self):
        request = self.factory.get(f'/plugins/ledger/expenses/split/add/?ledger={self.ledger.pk}')
        request.user = self.superuser

        response = ExpenseSplitView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.alice.name.encode(), response.content)
        self.assertIn(self.bob.name.encode(), response.content)

    def test_post_creates_expense_with_even_auto_split(self):
        request = self.factory.post('/plugins/ledger/expenses/split/add/', data=self._post_data())
        request.user = self.superuser

        response = ExpenseSplitView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get(name='Dinner')
        self.assertEqual(expense.amount, Decimal('100'))
        parts = {part.person: part for part in expense.parts.all()}
        self.assertEqual(parts[self.alice].should_pay, Decimal('50'))
        self.assertEqual(parts[self.bob].should_pay, Decimal('50'))
        self.assertEqual(parts[self.alice].has_paid, Decimal('100'))

    def test_post_distributes_odd_remainder_to_first_auto_person(self):
        # 100 split three ways with pure auto-split: 33.34 / 33.33 / 33.33
        carol = Person.objects.create(name='Carol', ledger=self.ledger)
        data = self._post_data(**{f'person-involved-{carol.pk}': 'on', f'person-auto-{carol.pk}': 'on'})

        request = self.factory.post('/plugins/ledger/expenses/split/add/', data=data)
        request.user = self.superuser
        response = ExpenseSplitView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get(name='Dinner')
        shares = sorted(part.should_pay for part in expense.parts.all())
        self.assertEqual(shares, [Decimal('33.33'), Decimal('33.33'), Decimal('33.34')])
        self.assertEqual(sum(shares), Decimal('100'))

    def test_post_rejects_shares_that_dont_add_up(self):
        data = self._post_data(**{
            f'person-auto-{self.alice.pk}': '',
            f'person-shouldpay-{self.alice.pk}': '10',
            f'person-auto-{self.bob.pk}': '',
            f'person-shouldpay-{self.bob.pk}': '10',
        })
        request = self.factory.post('/plugins/ledger/expenses/split/add/', data=data)
        request.user = self.superuser

        response = ExpenseSplitView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Expense.objects.filter(name='Dinner').exists())

    def test_post_edit_replaces_existing_parts(self):
        expense = Expense.objects.create(
            name='Old name',
            ledger=self.ledger,
            currency=self.currency,
            amount=Decimal('100'),
            amount_native=Decimal('100'),
            date='2026-01-01',
        )
        ExpensePart.objects.create(
            expense=expense, person=self.alice, has_paid=Decimal('100'), should_pay=Decimal('100')
        )

        request = self.factory.post(
            f'/plugins/ledger/expenses/{expense.pk}/split/',
            data=self._post_data(name='Dinner (renamed)'),
        )
        request.user = self.superuser
        response = ExpenseSplitView.as_view()(request, pk=expense.pk)

        self.assertEqual(response.status_code, 302)
        expense.refresh_from_db()
        self.assertEqual(expense.name, 'Dinner (renamed)')
        self.assertEqual(expense.parts.count(), 2)


class LedgerSettleUpViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = User.objects.create_user(username='settle-admin', password='pass', is_superuser=True)
        self.currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        self.ledger = Ledger.objects.create(name='Summer trip', currency=self.currency)
        self.alice = Person.objects.create(name='Alice', ledger=self.ledger)
        self.bob = Person.objects.create(name='Bob', ledger=self.ledger)

    def _get(self):
        request = self.factory.get(f'/plugins/ledger/ledgers/{self.ledger.pk}/settle-up/')
        request.user = self.superuser
        return LedgerSettleUpView.as_view()(request, pk=self.ledger.pk)

    def test_no_expenses_shows_empty_state(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No expenses recorded', response.content)

    def test_basic_method_computes_matrix(self):
        expense = Expense.objects.create(
            name='Dinner',
            ledger=self.ledger,
            currency=self.currency,
            amount=Decimal('100'),
            amount_native=Decimal('100'),
            date='2026-01-01',
        )
        ExpensePart.objects.create(
            expense=expense, person=self.alice, has_paid=Decimal('100'), has_paid_native=Decimal('100'),
            should_pay=Decimal('50'), should_pay_native=Decimal('50'),
        )
        ExpensePart.objects.create(
            expense=expense, person=self.bob, has_paid=Decimal('0'), has_paid_native=Decimal('0'),
            should_pay=Decimal('50'), should_pay_native=Decimal('50'),
        )

        response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Alice', response.content)
        self.assertIn(b'Bob', response.content)

    def test_optimized_method_computes_matrix(self):
        self.ledger.calc_method = 'optimized'
        self.ledger.save()
        expense = Expense.objects.create(
            name='Dinner',
            ledger=self.ledger,
            currency=self.currency,
            amount=Decimal('100'),
            amount_native=Decimal('100'),
            date='2026-01-01',
        )
        ExpensePart.objects.create(
            expense=expense, person=self.alice, has_paid=Decimal('100'), has_paid_native=Decimal('100'),
            should_pay=Decimal('50'), should_pay_native=Decimal('50'),
        )
        ExpensePart.objects.create(
            expense=expense, person=self.bob, has_paid=Decimal('0'), has_paid_native=Decimal('0'),
            should_pay=Decimal('50'), should_pay_native=Decimal('50'),
        )

        response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'Could not calculate', response.content)
