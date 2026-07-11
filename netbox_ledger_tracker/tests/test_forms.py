from decimal import Decimal

from django.test import TestCase

from netbox_ledger_tracker.forms import CurrencyForm, ExpenseSplitForm, LedgerPickerForm
from netbox_ledger_tracker.models import Currency, Expense, ExpensePart, Ledger, Person


class CurrencyFormTest(TestCase):
    def test_valid_code_is_accepted(self):
        form = CurrencyForm(data={'iso4217_code': 'DKK', 'base_rate': '1', 'comments': ''})
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_code_is_rejected(self):
        form = CurrencyForm(data={'iso4217_code': 'XX1', 'base_rate': '1', 'comments': ''})
        self.assertFalse(form.is_valid())


class LedgerPickerFormTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))

    def test_open_ledger_is_valid_choice(self):
        ledger = Ledger.objects.create(name='Summer trip', currency=self.currency)
        form = LedgerPickerForm(data={'ledger': ledger.pk})
        self.assertTrue(form.is_valid(), form.errors)

    def test_closed_ledger_is_excluded(self):
        ledger = Ledger.objects.create(name='House tab', currency=self.currency, closed=True)
        form = LedgerPickerForm(data={'ledger': ledger.pk})
        self.assertFalse(form.is_valid())


class ExpenseSplitFormTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(iso4217_code='DKK', base_rate=Decimal('1'))
        self.ledger = Ledger.objects.create(name='Summer trip', currency=self.currency)
        self.alice = Person.objects.create(name='Alice', ledger=self.ledger)
        self.bob = Person.objects.create(name='Bob', ledger=self.ledger)

    def test_add_person_fields_defaults_to_auto_split_uninvolved(self):
        form = ExpenseSplitForm()
        form.add_person_fields([self.alice, self.bob])
        self.assertFalse(form.fields[form.get_field_name(self.alice, 'involved')].initial)
        self.assertTrue(form.fields[form.get_field_name(self.alice, 'auto')].initial)

    def test_add_person_fields_prefills_from_existing_part(self):
        expense = Expense.objects.create(
            name='Dinner',
            ledger=self.ledger,
            currency=self.currency,
            amount=Decimal('100'),
            amount_native=Decimal('100'),
            date='2026-01-01',
        )
        part = ExpensePart.objects.create(
            expense=expense, person=self.alice, has_paid=Decimal('100'), should_pay=Decimal('60')
        )
        form = ExpenseSplitForm()
        form.add_person_fields([self.alice, self.bob], existing_parts={self.alice.pk: part})
        self.assertTrue(form.fields[form.get_field_name(self.alice, 'involved')].initial)
        self.assertEqual(form.fields[form.get_field_name(self.alice, 'haspaid')].initial, Decimal('100'))

    def test_get_involved_people_filters_by_checkbox(self):
        data = {
            'name': 'Dinner',
            'ledger': self.ledger.pk,
            'currency': self.currency.pk,
            'amount': '100',
            'date': '2026-01-01',
            f'person-involved-{self.alice.pk}': 'on',
            f'person-haspaid-{self.alice.pk}': '100',
            f'person-auto-{self.alice.pk}': 'on',
            f'person-auto-{self.bob.pk}': 'on',
        }
        form = ExpenseSplitForm(data=data)
        form.add_person_fields([self.alice, self.bob])
        self.assertTrue(form.is_valid(), form.errors)
        involved = form.get_involved_people([self.alice, self.bob])
        self.assertEqual(involved, [self.alice])
