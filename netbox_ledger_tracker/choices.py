from utilities.choices import ChoiceSet


class LedgerCalcMethodChoices(ChoiceSet):
    key = 'Ledger.calc_method'

    BASIC = 'basic'
    OPTIMIZED = 'optimized'

    CHOICES = [
        (BASIC, 'Basic (pairwise netting)', 'blue'),
        (OPTIMIZED, 'Optimized (minimum-cost settlement)', 'green'),
    ]
