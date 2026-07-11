from decimal import Decimal

from django.test import TestCase

from netbox_ledger_tracker.filtersets import (
    CurrencyFilterSet,
    ExpenseFilterSet,
    ExpensePartFilterSet,
    LedgerFilterSet,
    PersonFilterSet,
)
from netbox_ledger_tracker.models import Currency, Expense, ExpensePart, Ledger, Person


class CurrencyFilterSetTest(TestCase):
    queryset = Currency.objects.all()
    filterset = CurrencyFilterSet

    @classmethod
    def setUpTestData(cls):
        Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        Currency.objects.create(iso4217_code='EUR', base_rate=Decimal('7.45'))

    def test_iso4217_code(self):
        params = {'iso4217_code': 'dkk'}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search(self):
        params = {'q': 'EUR'}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class LedgerFilterSetTest(TestCase):
    queryset = Ledger.objects.all()
    filterset = LedgerFilterSet

    @classmethod
    def setUpTestData(cls):
        currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        Ledger.objects.create(name='Summer trip', currency=currency, closed=False)
        Ledger.objects.create(name='House tab', currency=currency, closed=True)

    def test_closed(self):
        params = {'closed': True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search(self):
        params = {'q': 'summer'}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class PersonFilterSetTest(TestCase):
    queryset = Person.objects.all()
    filterset = PersonFilterSet

    @classmethod
    def setUpTestData(cls):
        currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        ledger = Ledger.objects.create(name='Summer trip', currency=currency)
        Person.objects.create(name='Alice', ledger=ledger)
        Person.objects.create(name='Bob', ledger=ledger)

    def test_ledger_id(self):
        ledger = Ledger.objects.first()
        params = {'ledger_id': [ledger.pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        params = {'q': 'ali'}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class ExpenseFilterSetTest(TestCase):
    queryset = Expense.objects.all()
    filterset = ExpenseFilterSet

    @classmethod
    def setUpTestData(cls):
        currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        ledger = Ledger.objects.create(name='Summer trip', currency=currency)
        Expense.objects.create(
            name='Dinner',
            ledger=ledger,
            currency=currency,
            amount=Decimal('100'),
            amount_native=Decimal('100'),
            date='2026-01-01',
        )
        Expense.objects.create(
            name='Groceries',
            ledger=ledger,
            currency=currency,
            amount=Decimal('50'),
            amount_native=Decimal('50'),
            date='2026-01-05',
        )

    def test_search(self):
        params = {'q': 'dinner'}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_date_range(self):
        params = {'date_after': '2026-01-03'}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class ExpensePartFilterSetTest(TestCase):
    queryset = ExpensePart.objects.all()
    filterset = ExpensePartFilterSet

    @classmethod
    def setUpTestData(cls):
        currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        ledger = Ledger.objects.create(name='Summer trip', currency=currency)
        expense = Expense.objects.create(
            name='Dinner',
            ledger=ledger,
            currency=currency,
            amount=Decimal('100'),
            amount_native=Decimal('100'),
            date='2026-01-01',
        )
        person = Person.objects.create(name='Alice', ledger=ledger)
        ExpensePart.objects.create(expense=expense, person=person, should_pay=Decimal('50'))

    def test_expense_id(self):
        expense = Expense.objects.first()
        params = {'expense_id': [expense.pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
