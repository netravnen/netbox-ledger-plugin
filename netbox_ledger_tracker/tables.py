import django_tables2 as tables
from netbox.tables import NetBoxTable, columns

from .models import Currency, Expense, ExpensePart, Ledger, Person, Settlement


class CurrencyTable(NetBoxTable):
    iso4217_code = tables.Column(linkify=True, verbose_name='ISO 4217 code')

    class Meta(NetBoxTable.Meta):
        model = Currency
        fields = ('pk', 'id', 'iso4217_code', 'base_rate', 'comments', 'created', 'last_updated', 'tags')
        default_columns = ('iso4217_code', 'base_rate')


class LedgerTable(NetBoxTable):
    name = tables.Column(linkify=True)
    currency = tables.Column(linkify=True)
    closed = columns.BooleanColumn()
    calc_method = columns.ChoiceFieldColumn()
    people_count = tables.Column(verbose_name='People', empty_values=(), accessor='people__count')
    expenses_count = tables.Column(verbose_name='Expenses', empty_values=(), accessor='expenses__count')

    class Meta(NetBoxTable.Meta):
        model = Ledger
        fields = (
            'pk',
            'id',
            'name',
            'currency',
            'closed',
            'calc_method',
            'people_count',
            'expenses_count',
            'comments',
            'created',
            'last_updated',
            'tags',
        )
        default_columns = ('name', 'currency', 'closed', 'calc_method', 'people_count', 'expenses_count')


class PersonTable(NetBoxTable):
    name = tables.Column(linkify=True)
    ledger = tables.Column(linkify=True)
    user = tables.Column(linkify=True, verbose_name='NetBox user')

    class Meta(NetBoxTable.Meta):
        model = Person
        fields = ('pk', 'id', 'name', 'ledger', 'user', 'created', 'last_updated', 'tags')
        default_columns = ('name', 'ledger', 'user')


class ExpenseTable(NetBoxTable):
    name = tables.Column(linkify=True)
    ledger = tables.Column(linkify=True)
    currency = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = Expense
        fields = (
            'pk',
            'id',
            'name',
            'ledger',
            'currency',
            'amount',
            'amount_native',
            'date',
            'comments',
            'created',
            'last_updated',
            'tags',
        )
        default_columns = ('name', 'ledger', 'amount', 'currency', 'date')


class SettlementTable(NetBoxTable):
    pk = columns.ToggleColumn()
    ledger = tables.Column(linkify=True)
    from_person = tables.Column(linkify=True, verbose_name='From')
    to_person = tables.Column(linkify=True, verbose_name='To')
    currency = tables.Column(linkify=True)
    method = columns.ChoiceFieldColumn()

    class Meta(NetBoxTable.Meta):
        model = Settlement
        fields = (
            'pk',
            'id',
            'ledger',
            'from_person',
            'to_person',
            'amount',
            'currency',
            'amount_native',
            'date',
            'method',
            'comments',
            'created',
            'last_updated',
            'tags',
        )
        default_columns = ('date', 'ledger', 'from_person', 'to_person', 'amount', 'currency', 'method')


class ExpensePartTable(NetBoxTable):
    expense = tables.Column(linkify=True)
    person = tables.Column(linkify=True)
    auto_amount = columns.BooleanColumn(verbose_name='Auto Split')

    class Meta(NetBoxTable.Meta):
        model = ExpensePart
        fields = (
            'pk',
            'id',
            'expense',
            'person',
            'has_paid',
            'should_pay',
            'auto_amount',
            'created',
            'last_updated',
            'tags',
        )
        default_columns = ('expense', 'person', 'has_paid', 'should_pay', 'auto_amount')
