def basic_calc(expenses, people, settlements=None):
    """Naive pairwise debt netting.

    ``expenses`` is a list of dicts, each shaped like::

        {
            'whopaid': [{'personId': <id>, 'amount': Fraction(...)}, ...],
            'whoshouldpay': {<personId>: Fraction(...), ...},
        }

    ``settlements`` is a list of dicts shaped like
    ``{'from': <id>, 'to': <id>, 'amount': Fraction(...)}`` describing payments
    that have already been made.

    Returns a dict of dicts: ``debts[debtor_id][creditor_id] = amount owed``.
    Mutual debts between the same two people are netted against each other
    so only the net direction/amount remains.
    """
    debts = _pairwise_debts(expenses)

    if settlements:
        _record_settlements(debts, settlements)

    _net_mutual_debts(debts)

    return debts


def _pairwise_debts(expenses):
    """Accumulate each person's share as a debt to everyone who paid."""
    debts = {}

    for expense in expenses:
        for payer in expense['whopaid']:
            for split_person in expense['whoshouldpay']:
                debts.setdefault(split_person, {})

                if payer['personId'] != split_person:
                    share = expense['whoshouldpay'][split_person]
                    if payer['personId'] in debts[split_person]:
                        debts[split_person][payer['personId']] += share
                    else:
                        debts[split_person][payer['personId']] = share

    return debts


def _record_settlements(debts, settlements):
    """Book a payment from A to B as a debt from B back to A.

    Adding the reverse debt rather than subtracting the forward one lets the
    existing netting pass resolve it, and handles overpayment for free: pay back
    more than you owed and the balance simply flips direction.
    """
    for settlement in settlements:
        payer_id = settlement['from']
        receiver_id = settlement['to']
        debts.setdefault(receiver_id, {})
        debts[receiver_id].setdefault(payer_id, 0)
        debts[receiver_id][payer_id] += settlement['amount']


def _net_mutual_debts(debts):
    """Collapse two-way debts so only the net direction and amount remain."""
    for payer_id in list(debts):
        receiver_ids = list(debts[payer_id])
        for receiver_id in receiver_ids:
            debts.setdefault(payer_id, {})
            debts[payer_id].setdefault(receiver_id, 0)
            debts.setdefault(receiver_id, {})
            debts[receiver_id].setdefault(payer_id, 0)

            if payer_id == receiver_id:
                continue

            if debts[payer_id][receiver_id] == 0 or debts[receiver_id][payer_id] == 0:
                continue

            if debts[receiver_id][payer_id] > debts[payer_id][receiver_id]:
                debts[receiver_id][payer_id] -= debts[payer_id][receiver_id]
                debts[payer_id][receiver_id] = 0
            elif debts[receiver_id][payer_id] < debts[payer_id][receiver_id]:
                debts[payer_id][receiver_id] -= debts[receiver_id][payer_id]
                debts[receiver_id][payer_id] = 0
            else:
                debts[payer_id][receiver_id] = 0
                debts[receiver_id][payer_id] = 0
