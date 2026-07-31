from netbox.ui import attrs
from netbox.ui.panels import ObjectAttributesPanel


class CurrencyPanel(ObjectAttributesPanel):
    title = 'Currency'
    iso4217_code = attrs.TextAttr('iso4217_code', style='font-monospace', label='ISO 4217 code')
    base_rate = attrs.NumericAttr('base_rate', label='Base rate')


class LedgerPanel(ObjectAttributesPanel):
    title = 'Ledger'
    name = attrs.TextAttr('name')
    currency = attrs.RelatedObjectAttr('currency', linkify=True)
    closed = attrs.BooleanAttr('closed')
    calc_method = attrs.ChoiceAttr('calc_method', label='Calculation method')


class PersonPanel(ObjectAttributesPanel):
    title = 'Person'
    name = attrs.TextAttr('name')
    ledger = attrs.RelatedObjectAttr('ledger', linkify=True)
    user = attrs.RelatedObjectAttr('user', linkify=True, label='NetBox user')


class ExpensePanel(ObjectAttributesPanel):
    title = 'Expense'
    name = attrs.TextAttr('name')
    ledger = attrs.RelatedObjectAttr('ledger', linkify=True)
    currency = attrs.RelatedObjectAttr('currency', linkify=True)
    amount = attrs.NumericAttr('amount')
    amount_native = attrs.NumericAttr('amount_native', label='Amount (ledger currency)')
    date = attrs.TextAttr('date')


class ExpensePartPanel(ObjectAttributesPanel):
    title = 'Expense Part'
    expense = attrs.RelatedObjectAttr('expense', linkify=True)
    person = attrs.RelatedObjectAttr('person', linkify=True)
    has_paid = attrs.NumericAttr('has_paid', label='Paid')
    should_pay = attrs.NumericAttr('should_pay', label='Owes')
    auto_amount = attrs.BooleanAttr('auto_amount', label='Auto-split')


class SettlementPanel(ObjectAttributesPanel):
    title = 'Settlement'
    ledger = attrs.RelatedObjectAttr('ledger', linkify=True)
    from_person = attrs.RelatedObjectAttr('from_person', linkify=True, label='From')
    to_person = attrs.RelatedObjectAttr('to_person', linkify=True, label='To')
    amount = attrs.NumericAttr('amount')
    currency = attrs.RelatedObjectAttr('currency', linkify=True)
    amount_native = attrs.NumericAttr('amount_native', label='Amount (ledger currency)')
    date = attrs.TextAttr('date')
    method = attrs.ChoiceAttr('method')
