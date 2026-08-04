from netbox.search import SearchIndex, register
from . import models


@register
class LedgerIndex(SearchIndex):
    model = models.Ledger
    fields = (
        ('name', 100),
        ('description', 500),
        ('comments', 500),
    )


@register
class PersonIndex(SearchIndex):
    model = models.Person
    fields = (
        ('name', 100),
    )


@register
class ExpenseIndex(SearchIndex):
    model = models.Expense
    fields = (
        ('title', 100),
        ('vendor', 100),
        ('comments', 500),
    )


@register
class SettlementIndex(SearchIndex):
    model = models.Settlement
    fields = (
        ('title', 100),
        ('comments', 500),
    )
