import django_filters
from django.contrib.auth import get_user_model
from netbox.filtersets import NetBoxModelFilterSet

from .choices import LedgerCalcMethodChoices
from .models import Currency, Expense, ExpensePart, Ledger, Person

User = get_user_model()


class CurrencyFilterSet(NetBoxModelFilterSet):
    iso4217_code = django_filters.CharFilter(field_name='iso4217_code', lookup_expr='iexact')

    class Meta:
        model = Currency
        fields = ['id', 'iso4217_code', 'base_rate']

    def search(self, queryset, name, value):
        return queryset.filter(iso4217_code__icontains=value)


class LedgerFilterSet(NetBoxModelFilterSet):
    currency_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Currency.objects.all(),
        label='Currency (ID)',
    )
    currency = django_filters.ModelMultipleChoiceFilter(
        field_name='currency__iso4217_code',
        queryset=Currency.objects.all(),
        to_field_name='iso4217_code',
        label='Currency (ISO 4217 code)',
    )
    calc_method = django_filters.MultipleChoiceFilter(
        field_name='calc_method',
        choices=LedgerCalcMethodChoices,
    )

    class Meta:
        model = Ledger
        fields = ['id', 'name', 'closed', 'calc_method']

    def search(self, queryset, name, value):
        return queryset.filter(name__icontains=value)


class PersonFilterSet(NetBoxModelFilterSet):
    ledger_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Ledger.objects.all(),
        label='Ledger (ID)',
    )
    ledger = django_filters.ModelMultipleChoiceFilter(
        field_name='ledger__name',
        queryset=Ledger.objects.all(),
        to_field_name='name',
        label='Ledger (name)',
    )
    user_id = django_filters.ModelMultipleChoiceFilter(
        queryset=User.objects.all(),
        label='NetBox user (ID)',
    )

    class Meta:
        model = Person
        fields = ['id', 'name']

    def search(self, queryset, name, value):
        return queryset.filter(name__icontains=value)


class ExpenseFilterSet(NetBoxModelFilterSet):
    ledger_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Ledger.objects.all(),
        label='Ledger (ID)',
    )
    ledger = django_filters.ModelMultipleChoiceFilter(
        field_name='ledger__name',
        queryset=Ledger.objects.all(),
        to_field_name='name',
        label='Ledger (name)',
    )
    currency_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Currency.objects.all(),
        label='Currency (ID)',
    )
    date = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Expense
        fields = ['id', 'name', 'amount', 'date']

    def search(self, queryset, name, value):
        return queryset.filter(name__icontains=value)


class ExpensePartFilterSet(NetBoxModelFilterSet):
    expense_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Expense.objects.all(),
        label='Expense (ID)',
    )
    person_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Person.objects.all(),
        label='Person (ID)',
    )

    class Meta:
        model = ExpensePart
        fields = ['id', 'has_paid', 'should_pay', 'auto_amount']

    def search(self, queryset, name, value):
        return queryset.filter(person__name__icontains=value)
