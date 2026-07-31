from netbox.search import SearchIndex, register_search

from .models import Currency, Expense, Ledger, Person, Settlement


@register_search
class CurrencyIndex(SearchIndex):
    model = Currency
    fields = (('iso4217_code', 100), ('comments', 5000))


@register_search
class LedgerIndex(SearchIndex):
    model = Ledger
    fields = (('name', 100), ('comments', 5000))
    display_attrs = ('currency', 'closed', 'calc_method')


@register_search
class PersonIndex(SearchIndex):
    model = Person
    fields = (('name', 100),)
    display_attrs = ('ledger', 'user')


@register_search
class ExpenseIndex(SearchIndex):
    model = Expense
    fields = (('name', 100), ('comments', 5000))
    display_attrs = ('ledger', 'amount', 'date')


@register_search
class SettlementIndex(SearchIndex):
    model = Settlement
    fields = (('comments', 5000),)
    display_attrs = ('ledger', 'from_person', 'to_person', 'amount', 'date')
