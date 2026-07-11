from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from netbox_ledger_tracker.choices import LedgerCalcMethodChoices
from netbox_ledger_tracker.models import Currency, Expense, ExpensePart, Ledger, Person

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
