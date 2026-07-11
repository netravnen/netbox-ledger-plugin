from collections import OrderedDict
from decimal import Decimal


def result_to_matrix(result, people_by_id):
    """Arrange a ``{payer_id: {receiver_id: amount}}`` debt dict into a payer x receiver grid.

    ``people_by_id`` is an ordered ``{person_id: display_name}`` mapping. The
    returned matrix includes a header row/column plus "Total Pay"/"Total
    Receive" totals, ready for straightforward template rendering.
    """
    matrix = _empty_matrix(people_by_id)
    return _populate_matrix(result, matrix, people_by_id)


def _empty_matrix(people_by_id):
    matrix = OrderedDict()

    header_row = OrderedDict()
    header_row[0] = 'n/a'
    for person_id, name in people_by_id.items():
        header_row[person_id] = f'{name} pay'
    matrix[0] = header_row

    for receiver_id, receiver_name in people_by_id.items():
        row = OrderedDict()
        row[0] = f'{receiver_name} receive'
        for payer_id, payer_name in people_by_id.items():
            row[payer_id] = 'n/a' if payer_name == receiver_name else Decimal(0)
        matrix[receiver_id] = row

    return matrix


def _populate_matrix(result, matrix, people_by_id):
    pay_totals = OrderedDict((person_id, Decimal(0)) for person_id in people_by_id)
    receive_totals = OrderedDict((person_id, Decimal(0)) for person_id in people_by_id)

    for payer_id, receiver_amounts in result.items():
        for receiver_id, amount in receiver_amounts.items():
            pay_totals[payer_id] += amount
            receive_totals[receiver_id] += amount
            matrix[receiver_id][payer_id] = amount

    for receiver_id in matrix:
        if receiver_id == 0:
            matrix[0]['total'] = 'Total Receive'
        else:
            matrix[receiver_id]['total'] = receive_totals[receiver_id]

    totals_row = OrderedDict()
    totals_row[0] = 'Total Pay'
    for person_id in people_by_id:
        totals_row[person_id] = pay_totals[person_id]
    totals_row['total'] = 'n/a'
    matrix['total'] = totals_row

    return matrix
