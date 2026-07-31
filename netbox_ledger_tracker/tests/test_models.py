from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from netbox_ledger_tracker.choices import LedgerCalcMethodChoices
from netbox_ledger_tracker.models import Currency, Expense, ExpensePart, Ledger, Person, Settlement

User = get_user_model()


class CurrencyModelTest(TestCase):
    def test_iso4217_code_is_uppercased_on_save(self):
        currency = Currency.objects.create(iso4217_code='dkk', base_rate=Decimal('1'))
        currency.refresh_from_db()
        self.assertEqual(currency.iso4217_code, 'DKK')

    def test_invalid_code_fails_validation(self):
        currency = Currency(iso4217_code='D1', base_rate=Decimal('1'))
        with self.assertRaises(ValidationError):
            currency.full_clean()


class LedgerModelTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))

    def test_default_calc_method_is_basic(self):
        ledger = Ledger.objects.create(name='Summer trip', currency=self.currency)
        self.assertEqual(ledger.calc_method, LedgerCalcMethodChoices.BASIC)

    def test_str_returns_name(self):
        ledger = Ledger.objects.create(name='Summer trip', currency=self.currency)
        self.assertEqual(str(ledger), 'Summer trip')


class PersonModelTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        self.ledger = Ledger.objects.create(name='Summer trip', currency=self.currency)

    def test_name_unique_within_ledger(self):
        Person.objects.create(name='Alice', ledger=self.ledger)
        with self.assertRaises(ValidationError):
            duplicate = Person(name='Alice', ledger=self.ledger)
            duplicate.full_clean()

    def test_same_name_allowed_in_different_ledgers(self):
        other_ledger = Ledger.objects.create(name='House tab', currency=self.currency)
        Person.objects.create(name='Alice', ledger=self.ledger)
        # should not raise
        Person.objects.create(name='Alice', ledger=other_ledger)

    def test_user_link_is_optional(self):
        person = Person.objects.create(name='Alice', ledger=self.ledger)
        self.assertIsNone(person.user)


class ExpenseModelTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        self.ledger = Ledger.objects.create(name='Summer trip', currency=self.currency)

    def test_clean_rejects_closed_ledger(self):
        self.ledger.closed = True
        self.ledger.save()
        expense = Expense(
            name='Dinner',
            ledger=self.ledger,
            currency=self.currency,
            amount=Decimal('100'),
            amount_native=Decimal('100'),
            date='2026-01-01',
        )
        with self.assertRaises(ValidationError):
            expense.clean()

    def test_clean_allows_open_ledger(self):
        expense = Expense(
            name='Dinner',
            ledger=self.ledger,
            currency=self.currency,
            amount=Decimal('100'),
            amount_native=Decimal('100'),
            date='2026-01-01',
        )
        expense.clean()  # should not raise


class ExpenseCurrencyConversionTest(TestCase):
    """Conversion is derived by the model, so every write path gets it right."""

    def setUp(self):
        self.dkk = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        self.eur = Currency.objects.create(iso4217_code='EUR', base_rate=Decimal('7.46'))
        self.ledger = Ledger.objects.create(name='Summer trip', currency=self.dkk)

    def _expense(self, currency=None, amount='100.00'):
        return Expense.objects.create(
            name='Dinner',
            ledger=self.ledger,
            currency=currency or self.eur,
            amount=Decimal(amount),
            date='2026-01-01',
        )

    def test_save_converts_into_the_ledger_currency(self):
        expense = self._expense()
        self.assertEqual(expense.fx_rate, Decimal('7.4600000000'))
        self.assertEqual(expense.amount_native, Decimal('746.00'))

    def test_same_currency_uses_a_rate_of_one(self):
        expense = self._expense(currency=self.dkk)
        self.assertEqual(expense.fx_rate, Decimal('1.0000000000'))
        self.assertEqual(expense.amount_native, Decimal('100.00'))

    def test_editing_the_amount_keeps_the_frozen_rate(self):
        expense = self._expense()
        expense.amount = Decimal('200.00')
        expense.save()
        expense.refresh_from_db()
        self.assertEqual(expense.fx_rate, Decimal('7.4600000000'))
        self.assertEqual(expense.amount_native, Decimal('1492.00'))

    def test_later_rate_changes_do_not_reprice_a_saved_expense(self):
        expense = self._expense()
        self.eur.base_rate = Decimal('9.00')
        self.eur.save()

        expense.refresh_from_db()
        expense.save()
        expense.refresh_from_db()

        self.assertEqual(expense.fx_rate, Decimal('7.4600000000'))
        self.assertEqual(expense.amount_native, Decimal('746.00'))

    def test_changing_the_currency_rederives_the_rate(self):
        expense = self._expense()
        expense.currency = self.dkk
        expense.save()
        expense.refresh_from_db()
        self.assertEqual(expense.fx_rate, Decimal('1.0000000000'))
        self.assertEqual(expense.amount_native, Decimal('100.00'))

    def test_full_clean_populates_derived_fields(self):
        # clean_fields() runs before clean(), so the not-null derived columns have
        # to be filled in before validation rather than during it.
        expense = Expense(
            name='Dinner',
            ledger=self.ledger,
            currency=self.eur,
            amount=Decimal('100.00'),
            date='2026-01-01',
        )
        expense.full_clean()  # should not raise
        self.assertEqual(expense.amount_native, Decimal('746.00'))

    def test_parts_derive_natives_from_the_expense_rate(self):
        expense = self._expense()
        person = Person.objects.create(name='Alice', ledger=self.ledger)

        part = ExpensePart(expense=expense, person=person, has_paid=Decimal('100.00'), should_pay=Decimal('40.00'))
        part.save()
        part.refresh_from_db()

        self.assertEqual(part.has_paid_native, Decimal('746.00'))
        self.assertEqual(part.should_pay_native, Decimal('298.40'))

    def test_parts_ignore_caller_supplied_natives(self):
        expense = self._expense()
        person = Person.objects.create(name='Alice', ledger=self.ledger)

        part = ExpensePart(
            expense=expense,
            person=person,
            has_paid=Decimal('100.00'),
            has_paid_native=Decimal('1.00'),  # wrong on purpose
            should_pay=Decimal('100.00'),
            should_pay_native=Decimal('1.00'),
        )
        part.save()
        part.refresh_from_db()

        self.assertEqual(part.has_paid_native, Decimal('746.00'))
        self.assertEqual(part.should_pay_native, Decimal('746.00'))


class ExpensePartModelTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        self.ledger = Ledger.objects.create(name='Summer trip', currency=self.currency)
        self.other_ledger = Ledger.objects.create(name='House tab', currency=self.currency)
        self.expense = Expense.objects.create(
            name='Dinner',
            ledger=self.ledger,
            currency=self.currency,
            amount=Decimal('100'),
            amount_native=Decimal('100'),
            date='2026-01-01',
        )
        self.person = Person.objects.create(name='Alice', ledger=self.ledger)
        self.other_person = Person.objects.create(name='Bob', ledger=self.other_ledger)

    def test_clean_rejects_person_from_a_different_ledger(self):
        part = ExpensePart(expense=self.expense, person=self.other_person, should_pay=Decimal('50'))
        with self.assertRaises(ValidationError):
            part.clean()

    def test_clean_allows_person_from_the_same_ledger(self):
        part = ExpensePart(expense=self.expense, person=self.person, should_pay=Decimal('50'))
        part.clean()  # should not raise

    def test_unique_together_expense_person(self):
        ExpensePart.objects.create(expense=self.expense, person=self.person, should_pay=Decimal('50'))
        with self.assertRaises(ValidationError):
            duplicate = ExpensePart(expense=self.expense, person=self.person, should_pay=Decimal('50'))
            duplicate.full_clean()


class SettlementModelTest(TestCase):
    def setUp(self):
        self.dkk = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        self.eur = Currency.objects.create(iso4217_code='EUR', base_rate=Decimal('7.46'))
        self.ledger = Ledger.objects.create(name='Summer trip', currency=self.dkk)
        self.other_ledger = Ledger.objects.create(name='House tab', currency=self.dkk)
        self.alice = Person.objects.create(name='Alice', ledger=self.ledger)
        self.bob = Person.objects.create(name='Bob', ledger=self.ledger)
        self.outsider = Person.objects.create(name='Carol', ledger=self.other_ledger)

    def _settlement(self, **overrides):
        kwargs = {
            'ledger': self.ledger,
            'from_person': self.bob,
            'to_person': self.alice,
            'currency': self.dkk,
            'amount': Decimal('50.00'),
            'date': '2026-01-01',
        }
        kwargs.update(overrides)
        return Settlement(**kwargs)

    def test_converts_into_the_ledger_currency(self):
        settlement = self._settlement(currency=self.eur, amount=Decimal('10.00'))
        settlement.save()
        settlement.refresh_from_db()
        self.assertEqual(settlement.fx_rate, Decimal('7.4600000000'))
        self.assertEqual(settlement.amount_native, Decimal('74.60'))

    def test_later_rate_changes_do_not_reprice_a_saved_settlement(self):
        settlement = self._settlement(currency=self.eur, amount=Decimal('10.00'))
        settlement.save()

        self.eur.base_rate = Decimal('9.00')
        self.eur.save()
        settlement.refresh_from_db()
        settlement.save()
        settlement.refresh_from_db()

        self.assertEqual(settlement.fx_rate, Decimal('7.4600000000'))
        self.assertEqual(settlement.amount_native, Decimal('74.60'))

    def test_clean_rejects_paying_yourself(self):
        settlement = self._settlement(to_person=self.bob)
        with self.assertRaises(ValidationError):
            settlement.clean()

    def test_clean_rejects_a_person_from_another_ledger(self):
        settlement = self._settlement(from_person=self.outsider)
        with self.assertRaises(ValidationError):
            settlement.clean()

    def test_clean_rejects_closed_ledger(self):
        self.ledger.closed = True
        self.ledger.save()
        with self.assertRaises(ValidationError):
            self._settlement().clean()

    def test_clean_allows_a_valid_settlement(self):
        self._settlement().clean()  # should not raise

    def test_str_describes_the_transfer(self):
        self.assertEqual(str(self._settlement()), 'Bob to Alice: 50.00 DKK')


class ClosedLedgerTest(TestCase):
    """Ledger.closed promises to refuse new people; only expenses were checked."""

    def setUp(self):
        self.currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        self.open_ledger = Ledger.objects.create(name='Summer trip', currency=self.currency)
        self.closed_ledger = Ledger.objects.create(name='House tab', currency=self.currency, closed=True)

    def test_cannot_add_a_person_to_a_closed_ledger(self):
        with self.assertRaises(ValidationError):
            Person(name='Alice', ledger=self.closed_ledger).clean()

    def test_can_still_edit_an_existing_person_on_a_closed_ledger(self):
        # Added while the ledger was open, then the ledger was closed around them.
        person = Person.objects.create(name='Alice', ledger=self.open_ledger)
        self.open_ledger.closed = True
        self.open_ledger.save()

        person.refresh_from_db()
        person.name = 'Alice B'
        person.clean()  # should not raise

    def test_cannot_move_a_person_into_a_closed_ledger(self):
        person = Person.objects.create(name='Alice', ledger=self.open_ledger)
        person.ledger = self.closed_ledger
        with self.assertRaises(ValidationError):
            person.clean()

    def test_adding_to_an_open_ledger_is_fine(self):
        Person(name='Alice', ledger=self.open_ledger).clean()  # should not raise
