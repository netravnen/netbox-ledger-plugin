from utilities.choices import ChoiceSet, ColorChoices


class LedgerCalcMethodChoices(ChoiceSet):
    key = 'Ledger.calc_method'

    BASIC = 'basic'
    OPTIMIZED = 'optimized'
    MINIMAL = 'minimal'

    CHOICES = [
        (BASIC, 'Basic (pairwise netting)', ColorChoices.COLOR_BLUE),
        (OPTIMIZED, 'Optimized (minimum-cost settlement)', ColorChoices.COLOR_GREEN),
        (MINIMAL, 'Minimal (fewest payments)', ColorChoices.COLOR_PURPLE),
    ]


class SettlementMethodChoices(ChoiceSet):
    """How a settlement was actually paid. Informational only -- it does not
    affect the maths, but it is the first thing people ask when reconciling."""

    key = 'Settlement.method'

    CASH = 'cash'
    BANK_TRANSFER = 'bank_transfer'
    MOBILE_PAYMENT = 'mobile_payment'
    OTHER = 'other'

    CHOICES = [
        (CASH, 'Cash', ColorChoices.COLOR_GREEN),
        (BANK_TRANSFER, 'Bank transfer', ColorChoices.COLOR_BLUE),
        (MOBILE_PAYMENT, 'Mobile payment', ColorChoices.COLOR_PURPLE),
        (OTHER, 'Other', ColorChoices.COLOR_GRAY),
    ]
