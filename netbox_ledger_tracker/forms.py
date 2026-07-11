from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from netbox.forms import (
    NetBoxModelBulkEditForm,
    NetBoxModelFilterSetForm,
    NetBoxModelForm,
    NetBoxModelImportForm,
)
from utilities.forms.fields import (
    CSVModelChoiceField,
    DynamicModelChoiceField,
    TagFilterField,
)

from .choices import LedgerCalcMethodChoices
from .models import Currency, Expense, ExpensePart, Ledger, Person

User = get_user_model()

_NULL_BOOLEAN_CHOICES = ((None, '---------'), (True, 'Yes'), (False, 'No'))


###
# Currency
###


class CurrencyForm(NetBoxModelForm):
    class Meta:
        model = Currency
        fields = ['iso4217_code', 'base_rate', 'comments', 'tags']


class CurrencyImportForm(NetBoxModelImportForm):
    class Meta:
        model = Currency
        fields = ('iso4217_code', 'base_rate', 'comments', 'tags')


class CurrencyBulkEditForm(NetBoxModelBulkEditForm):
    model = Currency
    base_rate = forms.DecimalField(required=False, max_digits=20, decimal_places=6)
    comments = forms.CharField(required=False, widget=forms.Textarea)
    nullable_fields = ['comments']


class CurrencyFilterForm(NetBoxModelFilterSetForm):
    model = Currency
    iso4217_code = forms.CharField(required=False, label='ISO 4217 code')
    tag = TagFilterField(model)


###
# Ledger
###


class LedgerForm(NetBoxModelForm):
    currency = DynamicModelChoiceField(queryset=Currency.objects.all())

    class Meta:
        model = Ledger
        fields = ['name', 'currency', 'closed', 'calc_method', 'comments', 'tags']


class LedgerImportForm(NetBoxModelImportForm):
    currency = CSVModelChoiceField(
        queryset=Currency.objects.all(),
        to_field_name='iso4217_code',
        help_text='ISO 4217 code of the ledger currency',
    )

    class Meta:
        model = Ledger
        fields = ('name', 'currency', 'closed', 'calc_method', 'comments', 'tags')


class LedgerBulkEditForm(NetBoxModelBulkEditForm):
    model = Ledger
    currency = DynamicModelChoiceField(queryset=Currency.objects.all(), required=False)
    closed = forms.NullBooleanField(required=False, widget=forms.Select(choices=_NULL_BOOLEAN_CHOICES))
    calc_method = forms.ChoiceField(choices=[('', '---------'), *LedgerCalcMethodChoices], required=False)
    comments = forms.CharField(required=False, widget=forms.Textarea)
    nullable_fields = ['comments']


class LedgerFilterForm(NetBoxModelFilterSetForm):
    model = Ledger
    currency_id = DynamicModelChoiceField(queryset=Currency.objects.all(), required=False, label='Currency')
    closed = forms.NullBooleanField(required=False, widget=forms.Select(choices=_NULL_BOOLEAN_CHOICES))
    calc_method = forms.ChoiceField(choices=[('', '---------'), *LedgerCalcMethodChoices], required=False)
    tag = TagFilterField(model)


###
# Person
###


class PersonForm(NetBoxModelForm):
    ledger = DynamicModelChoiceField(queryset=Ledger.objects.all())
    user = DynamicModelChoiceField(queryset=User.objects.all(), required=False, label='NetBox user')

    class Meta:
        model = Person
        fields = ['name', 'ledger', 'user', 'tags']


class PersonImportForm(NetBoxModelImportForm):
    ledger = CSVModelChoiceField(queryset=Ledger.objects.all(), to_field_name='name')
    user = CSVModelChoiceField(
        queryset=User.objects.all(),
        to_field_name='username',
        required=False,
    )

    class Meta:
        model = Person
        fields = ('name', 'ledger', 'user', 'tags')


class PersonBulkEditForm(NetBoxModelBulkEditForm):
    model = Person
    ledger = DynamicModelChoiceField(queryset=Ledger.objects.all(), required=False)
    user = DynamicModelChoiceField(queryset=User.objects.all(), required=False, label='NetBox user')
    nullable_fields = ['user']


class PersonFilterForm(NetBoxModelFilterSetForm):
    model = Person
    ledger_id = DynamicModelChoiceField(queryset=Ledger.objects.all(), required=False, label='Ledger')
    user_id = DynamicModelChoiceField(queryset=User.objects.all(), required=False, label='NetBox user')
    tag = TagFilterField(model)


###
# Expense
###


class ExpenseForm(NetBoxModelForm):
    """Quick header-only edit form (name/amount/currency/date). Use Split Expense for the per-person breakdown."""

    ledger = DynamicModelChoiceField(queryset=Ledger.objects.all())
    currency = DynamicModelChoiceField(queryset=Currency.objects.all())

    class Meta:
        model = Expense
        fields = ['name', 'ledger', 'currency', 'amount', 'date', 'comments', 'tags']


class ExpenseImportForm(NetBoxModelImportForm):
    ledger = CSVModelChoiceField(queryset=Ledger.objects.all(), to_field_name='name')
    currency = CSVModelChoiceField(queryset=Currency.objects.all(), to_field_name='iso4217_code')

    class Meta:
        model = Expense
        fields = ('name', 'ledger', 'currency', 'amount', 'date', 'comments', 'tags')

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.amount_native = instance.amount
        if commit:
            instance.save()
        return instance


class ExpenseBulkEditForm(NetBoxModelBulkEditForm):
    model = Expense
    currency = DynamicModelChoiceField(queryset=Currency.objects.all(), required=False)
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    comments = forms.CharField(required=False, widget=forms.Textarea)
    nullable_fields = ['comments']


class ExpenseFilterForm(NetBoxModelFilterSetForm):
    model = Expense
    ledger_id = DynamicModelChoiceField(queryset=Ledger.objects.all(), required=False, label='Ledger')
    currency_id = DynamicModelChoiceField(queryset=Currency.objects.all(), required=False, label='Currency')
    tag = TagFilterField(model)


###
# ExpensePart
###


class ExpensePartForm(NetBoxModelForm):
    """Manual single-row edit. Most expense splits are created via the Split Expense form instead."""

    expense = DynamicModelChoiceField(queryset=Expense.objects.all())
    person = DynamicModelChoiceField(queryset=Person.objects.all(), query_params={'ledger_id': '$expense__ledger_id'})

    class Meta:
        model = ExpensePart
        fields = ['expense', 'person', 'has_paid', 'should_pay', 'auto_amount', 'tags']


class ExpensePartBulkEditForm(NetBoxModelBulkEditForm):
    model = ExpensePart
    has_paid = forms.DecimalField(required=False, max_digits=20, decimal_places=2)
    should_pay = forms.DecimalField(required=False, max_digits=20, decimal_places=2)
    auto_amount = forms.NullBooleanField(required=False, widget=forms.Select(choices=_NULL_BOOLEAN_CHOICES))


class ExpensePartFilterForm(NetBoxModelFilterSetForm):
    model = ExpensePart
    expense_id = DynamicModelChoiceField(queryset=Expense.objects.all(), required=False, label='Expense')
    person_id = DynamicModelChoiceField(queryset=Person.objects.all(), required=False, label='Person')
    tag = TagFilterField(model)


###
# Custom: split an Expense across multiple people in one form
###


class LedgerPickerForm(forms.Form):
    """Tiny GET-submitted form used to pick a ledger before showing ExpenseSplitForm.

    ExpenseSplitForm's per-person fields are keyed by person pk and only make
    sense once we know which ledger (and therefore which people) are in
    scope, so the split screen is a two-step flow when no ledger is known yet
    (matching the original app, where "add expense" always lived under a
    specific ledger's URL).
    """

    ledger = DynamicModelChoiceField(queryset=Ledger.objects.exclude(closed=True))


class ExpenseSplitForm(forms.Form):
    """Create (or replace) the full per-person breakdown of a shared expense in one screen.

    Mirrors the original buddyledger "add expense" UX: every person in the
    ledger gets an "involved" checkbox plus paid/owed fields, so who's
    included and how much they owe are set in a single submission.
    """

    name = forms.CharField(max_length=100)
    ledger = DynamicModelChoiceField(queryset=Ledger.objects.exclude(closed=True))
    currency = DynamicModelChoiceField(queryset=Currency.objects.all())
    amount = forms.DecimalField(min_value=0.01, decimal_places=2, max_digits=20)
    date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(attrs={'type': 'date'}))
    comments = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        self.expense = kwargs.pop('expense', None)
        super().__init__(*args, **kwargs)

    def get_field_name(self, person, field):
        return f'person-{field}-{person.pk}'

    def add_person_fields(self, people, existing_parts=None):
        """Attach the dynamic per-person involved/paid/share fields for the given people."""
        existing_parts = existing_parts or {}
        for person in people:
            part = existing_parts.get(person.pk)
            self.fields[self.get_field_name(person, 'involved')] = forms.BooleanField(
                label=person.name,
                required=False,
                initial=bool(part),
            )
            self.fields[self.get_field_name(person, 'haspaid')] = forms.DecimalField(
                label='Paid',
                required=False,
                min_value=0,
                decimal_places=2,
                initial=part.has_paid if part else 0,
            )
            self.fields[self.get_field_name(person, 'auto')] = forms.BooleanField(
                label='Auto-split remainder',
                required=False,
                initial=part.auto_amount if part else True,
            )
            self.fields[self.get_field_name(person, 'shouldpay')] = forms.DecimalField(
                label='Owes (if not auto-split)',
                required=False,
                min_value=0,
                decimal_places=2,
                initial=part.should_pay if part else None,
            )

    def get_involved_people(self, people):
        """Return the subset of ``people`` whose "involved" checkbox is checked."""
        return [person for person in people if self.cleaned_data.get(self.get_field_name(person, 'involved'))]

    def get_parts(self, people):
        """Return ``{person: {'has_paid': Decimal, 'auto_amount': bool, 'should_pay': Decimal|None}}``."""
        parts = {}
        for person in people:
            has_paid = self.cleaned_data.get(self.get_field_name(person, 'haspaid')) or 0
            auto_amount = bool(self.cleaned_data.get(self.get_field_name(person, 'auto')))
            should_pay = self.cleaned_data.get(self.get_field_name(person, 'shouldpay'))
            parts[person] = {
                'has_paid': has_paid,
                'auto_amount': auto_amount,
                'should_pay': None if auto_amount else (should_pay or 0),
            }
        return parts
