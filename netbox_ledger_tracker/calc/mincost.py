import itertools
from collections import defaultdict
from fractions import Fraction

import networkx as nx


def force_feasible(expenses, people):
    """Add a synthetic person involved in every expense, which will often (if not always) make the problem feasible."""
    synthetic_id = next(itertools.islice(filter(lambda x: x not in people, itertools.count(88888888)), 1))

    def add_synthetic(whoshouldpay):
        whoshouldpay.update({synthetic_id: None})
        return whoshouldpay

    padded_expenses = [
        {'whopaid': expense['whopaid'], 'whoshouldpay': add_synthetic(dict(expense['whoshouldpay']))}
        for expense in expenses
    ]
    return solve_mincost_problem_for_expenses(padded_expenses, [synthetic_id, *people])


def solve_mincost_problem_for_expenses(expenses, people):
    """Minimum-cost-flow settlement: fewest/cheapest transfers that settle every debt.

    ``expenses`` is a list of dicts shaped like::

        {
            'whopaid': [{'personId': <id>, 'amount': Fraction(...)}, ...],
            'whoshouldpay': {<personId>: Fraction(...) | None, ...},
        }

    A ``None`` share means "split the remainder of this expense evenly among
    everyone with a ``None`` share". Raises ``networkx.NetworkXUnfeasible`` if
    the supplied shares are inconsistent (don't sum to the paid total); see
    ``force_feasible`` for a workaround.
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

    graph = nx.DiGraph()
    for person_id, balance in balances.items():
        graph.add_node(person_id, demand=balance)

    graph.add_weighted_edges_from(pair + (1,) for pair in itertools.permutations(people, 2))

    _flow_cost, flow_dict = nx.network_simplex(graph)
    return flow_dict
