"""Net position per person, before any settlement is proposed.

Kept separate from the solvers because both of them, and the balance display,
need the same numbers. Deriving them twice would let the Settle Up matrix and
the per-person totals disagree, which is exactly the kind of discrepancy a
ledger cannot afford.
"""

from collections import defaultdict
from fractions import Fraction

__all__ = ('apply_settlements', 'compute_balances')


def compute_balances(expenses, people):
    """Return ``{person_id: Fraction}``: what each person is owed, net of expenses.

    Positive means they paid more than their share and are owed money; negative
    means they owe. ``expenses`` is a list of dicts shaped like::

        {
            'whopaid': [{'personId': <id>, 'amount': Fraction(...)}, ...],
            'whoshouldpay': {<personId>: Fraction(...) | None, ...},
        }

    A ``None`` share means "split whatever is left of this expense evenly among
    everyone whose share is ``None``".
    """
    balances = defaultdict(lambda: 0)

    for expense in expenses:
        whopaid = expense['whopaid']
        whoshouldpay = expense['whoshouldpay']
        total = sum(payment['amount'] for payment in whopaid)

        for person_id in people:
            if person_id in whoshouldpay:
                if whoshouldpay[person_id] is not None:
                    ideal_share = whoshouldpay[person_id]
                else:
                    fixed_shares = [share for share in whoshouldpay.values() if share is not None]
                    auto_count = len(whoshouldpay) - len(fixed_shares)
                    ideal_share = Fraction(total - sum(fixed_shares), auto_count)
            else:
                ideal_share = 0

            actual_paid = sum(payment['amount'] for payment in whopaid if payment['personId'] == person_id)
            balances[person_id] += actual_paid - ideal_share

    return balances


def apply_settlements(balances, settlements):
    """Fold already-made payments into ``balances``, returning a new mapping.

    ``settlements`` is a list of dicts shaped like::

        {'from': <person_id>, 'to': <person_id>, 'amount': Fraction(...)}

    Handing money over has the same effect on a balance as paying an expense:
    the payer has now put in more than they consumed, so their balance rises and
    the recipient's falls by the same amount. A settlement that exactly covers a
    debt therefore drives both parties to zero and they drop out of the result.
    """
    adjusted = defaultdict(lambda: 0)
    adjusted.update(balances)

    for settlement in settlements:
        adjusted[settlement['from']] += settlement['amount']
        adjusted[settlement['to']] -= settlement['amount']

    return adjusted
