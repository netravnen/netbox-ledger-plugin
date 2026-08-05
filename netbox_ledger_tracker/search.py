from netbox.search import SearchIndex, register_search
from . import models


@register_search
class LedgerIndex(SearchIndex):
    model = models.Ledger
    fields = (
        ('name', 100),
        ('description', 500),
        ('comments', 500),
    )


@register_search
class PersonIndex(SearchIndex):
    model = models.Person
    fields = (
        ('name', 100),
    )


@register_search
class ExpenseIndex(SearchIndex):
    model = models.Expense
    fields = (
        ('title', 100),
        ('vendor', 100),
        ('comments', 500),
    )


@register_search
class SettlementIndex(SearchIndex):
    model = models.Settlement
    fields = (
        ('title', 100),
        ('comments', 500),
    )
