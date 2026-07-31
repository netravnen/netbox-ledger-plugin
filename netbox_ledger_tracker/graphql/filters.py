import strawberry_django
from strawberry import auto

from .. import models


@strawberry_django.filter_type(models.Currency, lookups=True)
class CurrencyGraphQLFilter:
    iso4217_code: auto
    base_rate: auto


@strawberry_django.filter_type(models.Ledger, lookups=True)
class LedgerGraphQLFilter:
    name: auto
    currency: auto
    closed: auto
    calc_method: auto


@strawberry_django.filter_type(models.Person, lookups=True)
class PersonGraphQLFilter:
    name: auto
    ledger: auto
    user: auto


@strawberry_django.filter_type(models.Expense, lookups=True)
class ExpenseGraphQLFilter:
    name: auto
    ledger: auto
    currency: auto
    amount: auto
    date: auto


@strawberry_django.filter_type(models.ExpensePart, lookups=True)
class ExpensePartGraphQLFilter:
    expense: auto
    person: auto
    has_paid: auto
    should_pay: auto
    auto_amount: auto


@strawberry_django.filter_type(models.Settlement, lookups=True)
class SettlementGraphQLFilter:
    ledger: auto
    from_person: auto
    to_person: auto
    currency: auto
    amount: auto
    date: auto
    method: auto
