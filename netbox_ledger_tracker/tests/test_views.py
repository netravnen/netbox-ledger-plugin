from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from netbox_ledger_tracker.models import Currency, Expense, ExpensePart, Ledger, Person, Settlement

User = get_user_model()


def _url(name, **kwargs):
    return reverse(f'plugins:netbox_ledger_tracker:{name}', kwargs=kwargs or None)


class ListViewSmokeTest(TestCase):
    """Every model's list view should render for a superuser without error."""

    def setUp(self):
        self.superuser = User.objects.create_user(username='ledger-admin', password='pass', is_superuser=True)
        # Drive these through the test client rather than RequestFactory: the list
        # views call htmx_partial(), which reads request.htmx, and that attribute is
        # only set by django-htmx's middleware.
        self.client.force_login(self.superuser)
        self.currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        self.ledger = Ledger.objects.create(name='Summer trip', currency=self.currency)
        Person.objects.create(name='Alice', ledger=self.ledger)

    def test_currency_list(self):
        self.assertEqual(self.client.get(_url('currency_list')).status_code, 200)

    def test_ledger_list(self):
        self.assertEqual(self.client.get(_url('ledger_list')).status_code, 200)

    def test_person_list(self):
        self.assertEqual(self.client.get(_url('person_list')).status_code, 200)

    def test_expense_list(self):
        self.assertEqual(self.client.get(_url('expense_list')).status_code, 200)


class ExpenseSplitViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_user(username='split-admin', password='pass', is_superuser=True)
        # The success path calls messages.success(), which needs MessageMiddleware.
        self.client.force_login(self.superuser)
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
        response = self.client.get(_url('expense_split_add'))

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pick which ledger', response.content)

    def test_get_with_ledger_shows_person_fields(self):
        response = self.client.get(_url('expense_split_add'), {'ledger': self.ledger.pk})

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.alice.name.encode(), response.content)
        self.assertIn(self.bob.name.encode(), response.content)

    def test_post_creates_expense_with_even_auto_split(self):
        response = self.client.post(_url('expense_split_add'), data=self._post_data())

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

        response = self.client.post(_url('expense_split_add'), data=data)

        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get(name='Dinner')
        shares = sorted(part.should_pay for part in expense.parts.all())
        self.assertEqual(shares, [Decimal('33.33'), Decimal('33.33'), Decimal('33.34')])
        self.assertEqual(sum(shares), Decimal('100'))

    def test_post_rejects_shares_that_dont_add_up(self):
        data = self._post_data(
            **{
                f'person-auto-{self.alice.pk}': '',
                f'person-shouldpay-{self.alice.pk}': '10',
                f'person-auto-{self.bob.pk}': '',
                f'person-shouldpay-{self.bob.pk}': '10',
            }
        )

        response = self.client.post(_url('expense_split_add'), data=data)

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

        response = self.client.post(
            _url('expense_split_edit', pk=expense.pk),
            data=self._post_data(name='Dinner (renamed)'),
        )

        self.assertEqual(response.status_code, 302)
        expense.refresh_from_db()
        self.assertEqual(expense.name, 'Dinner (renamed)')
        self.assertEqual(expense.parts.count(), 2)


class LedgerSettleUpViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_user(username='settle-admin', password='pass', is_superuser=True)
        self.client.force_login(self.superuser)
        self.currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        self.ledger = Ledger.objects.create(name='Summer trip', currency=self.currency)
        self.alice = Person.objects.create(name='Alice', ledger=self.ledger)
        self.bob = Person.objects.create(name='Bob', ledger=self.ledger)

    def _get(self):
        return self.client.get(_url('ledger_settle_up', pk=self.ledger.pk))

    def _dinner_split_evenly(self):
        expense = Expense.objects.create(
            name='Dinner',
            ledger=self.ledger,
            currency=self.currency,
            amount=Decimal('100'),
            amount_native=Decimal('100'),
            date='2026-01-01',
        )
        ExpensePart.objects.create(
            expense=expense,
            person=self.alice,
            has_paid=Decimal('100'),
            has_paid_native=Decimal('100'),
            should_pay=Decimal('50'),
            should_pay_native=Decimal('50'),
        )
        ExpensePart.objects.create(
            expense=expense,
            person=self.bob,
            has_paid=Decimal('0'),
            has_paid_native=Decimal('0'),
            should_pay=Decimal('50'),
            should_pay_native=Decimal('50'),
        )
        return expense

    def test_no_expenses_shows_empty_state(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No expenses recorded', response.content)

    def test_basic_method_computes_matrix(self):
        self._dinner_split_evenly()

        response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Alice', response.content)
        self.assertIn(b'Bob', response.content)

    def test_optimized_method_computes_matrix(self):
        self.ledger.calc_method = 'optimized'
        self.ledger.save()
        self._dinner_split_evenly()

        response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'Could not calculate', response.content)

    def _settle(self, amount):
        return Settlement.objects.create(
            ledger=self.ledger,
            from_person=self.bob,
            to_person=self.alice,
            currency=self.currency,
            amount=Decimal(amount),
            date='2026-01-02',
        )

    def _matrix(self, response):
        return response.context['matrix']

    def test_settlement_is_deducted_under_basic(self):
        self._dinner_split_evenly()
        self._settle('50.00')

        response = self._get()

        self.assertEqual(response.status_code, 200)
        # Bob owed Alice 50 and has now paid it, so nothing is left outstanding.
        self.assertEqual(self._matrix(response)[self.alice.pk][self.bob.pk], Decimal('0.00'))
        self.assertIn(b'already been deducted', response.content)

    def test_partial_settlement_leaves_the_remainder_under_basic(self):
        self._dinner_split_evenly()
        self._settle('20.00')

        response = self._get()

        self.assertEqual(self._matrix(response)[self.alice.pk][self.bob.pk], Decimal('30.00'))

    def test_settlement_is_deducted_under_optimized(self):
        self.ledger.calc_method = 'optimized'
        self.ledger.save()
        self._dinner_split_evenly()
        self._settle('50.00')

        response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._matrix(response)[self.alice.pk][self.bob.pk], Decimal('0.00'))

    def test_no_banner_when_nothing_has_been_settled(self):
        self._dinner_split_evenly()
        self.assertNotIn(b'already been deducted', self._get().content)
