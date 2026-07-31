from utilities.choices import ChoiceSet


class LedgerCalcMethodChoices(ChoiceSet):
    key = 'Ledger.calc_method'

    BASIC = 'basic'
    OPTIMIZED = 'optimized'

    CHOICES = [
        (BASIC, 'Basic (pairwise netting)', 'blue'),
        (OPTIMIZED, 'Optimized (minimum-cost settlement)', 'green'),
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
        (CASH, 'Cash', 'green'),
        (BANK_TRANSFER, 'Bank transfer', 'blue'),
        (MOBILE_PAYMENT, 'Mobile payment', 'purple'),
        (OTHER, 'Other', 'gray'),
    ]
