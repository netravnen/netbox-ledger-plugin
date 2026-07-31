"""ORM-facing glue between the ledger models and the framework-free ``calc`` package.

Both the Settle Up matrix and the per-person balance tables are built from the
values here. Deriving them separately would let the two disagree -- a table
saying Alice is owed 250 next to a matrix that settles 300 is the kind of
discrepancy that destroys trust in the whole ledger -- so there is exactly one
place that turns rows into calculator input.
"""

from decimal import Decimal
from fractions import Fraction

from .calc.balances import apply_settlements, compute_balances
from .models import Expense, Person, Settlement

__all__ = ('build_ledger_calc_inputs', 'ledger_person_balances')


def build_ledger_calc_inputs(ledger):
    """Return ``(expense_data, settlement_data, inconsistent_expense_ids)`` for a ledger.

    Amounts are taken from the ``*_native`` columns, so everything is already in
    the ledger currency. An expense whose payments or shares do not add up to its
    total is reported rather than silently skewing the result.
    """
    expense_data = []
    inconsistent_expense_ids = []

    expenses = Expense.objects.filter(ledger=ledger).prefetch_related('parts')
    for expense in expenses:
        whopaid = []
        whoshouldpay = {}
        paid_total = Decimal('0')
        should_total = Decimal('0')

        for part in expense.parts.all():
            if part.has_paid_native:
                whopaid.append({'personId': part.person_id, 'amount': Fraction(part.has_paid_native)})
                paid_total += part.has_paid_native
            whoshouldpay[part.person_id] = Fraction(part.should_pay_native or 0)
            should_total += part.should_pay_native or 0

        if paid_total != expense.amount_native or should_total != expense.amount_native:
            inconsistent_expense_ids.append(expense.pk)

        expense_data.append({'whopaid': whopaid, 'whoshouldpay': whoshouldpay})

    settlement_data = [
        {
            'from': settlement.from_person_id,
            'to': settlement.to_person_id,
            'amount': Fraction(settlement.amount_native),
        }
        for settlement in Settlement.objects.filter(ledger=ledger)
    ]

    return expense_data, settlement_data, inconsistent_expense_ids


def ledger_person_balances(ledger, people=None):
    """Return a per-person breakdown, in ledger currency, ordered as ``people``.

    Each row carries ``paid`` (what they fronted on expenses), ``share`` (what
    those expenses say they owe), ``settled`` (net money they have since handed
    over, negative if they were paid) and ``net``. A positive ``net`` means they
    are owed; negative means they owe.

    ``net`` comes from the same calculator the Settle Up matrix uses rather than
    being recomputed from the three columns, so the two can never disagree.
    """
    if people is None:
        people = Person.objects.filter(ledger=ledger)
    people = list(people)

    expense_data, settlement_data, _ = build_ledger_calc_inputs(ledger)
    person_ids = [person.pk for person in people]

    balances = apply_settlements(compute_balances(expense_data, person_ids), settlement_data)

    paid = dict.fromkeys(person_ids, Decimal('0'))
    share = dict.fromkeys(person_ids, Decimal('0'))
    settled = dict.fromkeys(person_ids, Decimal('0'))

    for expense in Expense.objects.filter(ledger=ledger).prefetch_related('parts'):
        for part in expense.parts.all():
            if part.person_id in paid:
                paid[part.person_id] += part.has_paid_native or Decimal('0')
                share[part.person_id] += part.should_pay_native or Decimal('0')

    for settlement in Settlement.objects.filter(ledger=ledger):
        if settlement.from_person_id in settled:
            settled[settlement.from_person_id] += settlement.amount_native
        if settlement.to_person_id in settled:
            settled[settlement.to_person_id] -= settlement.amount_native

    return [
        {
            'person': person,
            'paid': paid[person.pk],
            'share': share[person.pk],
            'settled': settled[person.pk],
            'net': Decimal(balances[person.pk].numerator) / Decimal(balances[person.pk].denominator)
            if isinstance(balances[person.pk], Fraction)
            else Decimal(balances[person.pk]),
        }
        for person in people
    ]
