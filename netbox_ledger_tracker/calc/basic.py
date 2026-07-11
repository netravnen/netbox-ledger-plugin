def basic_calc(expenses, people):
    """Naive pairwise debt netting.

    ``expenses`` is a list of dicts, each shaped like::

        {
            'whopaid': [{'personId': <id>, 'amount': Fraction(...)}, ...],
            'whoshouldpay': {<personId>: Fraction(...), ...},
        }

    Returns a dict of dicts: ``debts[debtor_id][creditor_id] = amount owed``.
    Mutual debts between the same two people are netted against each other
    so only the net direction/amount remains.
    """
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

    # net out mutual debts so two people owing each other don't both show a balance
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

    return debts
