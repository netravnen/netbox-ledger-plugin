import strawberry_django
from netbox.graphql.types import NetBoxObjectType

from .. import models
from .filters import (
    CurrencyGraphQLFilter,
    ExpenseGraphQLFilter,
    ExpensePartGraphQLFilter,
    LedgerGraphQLFilter,
    PersonGraphQLFilter,
    SettlementGraphQLFilter,
)


@strawberry_django.type(
    models.Currency,
    fields='__all__',
    filters=CurrencyGraphQLFilter,
)
class CurrencyType(NetBoxObjectType):
    pass


@strawberry_django.type(
    models.Ledger,
    fields='__all__',
    filters=LedgerGraphQLFilter,
)
class LedgerType(NetBoxObjectType):
    pass


@strawberry_django.type(
    models.Person,
    fields='__all__',
    filters=PersonGraphQLFilter,
)
class PersonType(NetBoxObjectType):
    pass


@strawberry_django.type(
    models.Expense,
    fields='__all__',
    filters=ExpenseGraphQLFilter,
)
class ExpenseType(NetBoxObjectType):
    pass


@strawberry_django.type(
    models.ExpensePart,
    fields='__all__',
    filters=ExpensePartGraphQLFilter,
)
class ExpensePartType(NetBoxObjectType):
    pass


@strawberry_django.type(
    models.Settlement,
    fields='__all__',
    filters=SettlementGraphQLFilter,
)
class SettlementType(NetBoxObjectType):
    pass
