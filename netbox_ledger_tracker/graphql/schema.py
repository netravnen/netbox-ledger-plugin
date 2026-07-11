import strawberry
import strawberry_django

from .types import CurrencyType, ExpensePartType, ExpenseType, LedgerType, PersonType


# Keep the GraphQL root type named "Query" (matching the other plugins and the
# standalone-schema introspection in tests) while giving the Python class a
# plugin-distinct name.
@strawberry.type(name='Query')
class LedgerTrackerQuery:
    currency: CurrencyType = strawberry_django.field()
    currency_list: list[CurrencyType] = strawberry_django.field()

    ledger: LedgerType = strawberry_django.field()
    ledger_list: list[LedgerType] = strawberry_django.field()

    person: PersonType = strawberry_django.field()
    person_list: list[PersonType] = strawberry_django.field()

    expense: ExpenseType = strawberry_django.field()
    expense_list: list[ExpenseType] = strawberry_django.field()

    expense_part: ExpensePartType = strawberry_django.field()
    expense_part_list: list[ExpensePartType] = strawberry_django.field()


schema = strawberry.Schema(query=LedgerTrackerQuery)
