import itertools

import networkx as nx

from .balances import apply_settlements, compute_balances


def force_feasible(expenses, people, settlements=None):
    """Add a synthetic person involved in every expense, which will often (if not always) make the problem feasible."""
    synthetic_id = next(itertools.islice(filter(lambda x: x not in people, itertools.count(88888888)), 1))

    def add_synthetic(whoshouldpay):
        whoshouldpay.update({synthetic_id: None})
        return whoshouldpay

    padded_expenses = [
        {'whopaid': expense['whopaid'], 'whoshouldpay': add_synthetic(dict(expense['whoshouldpay']))}
        for expense in expenses
    ]
    return solve_mincost_problem_for_expenses(padded_expenses, [synthetic_id, *people], settlements=settlements)


def solve_from_balances(balances, people):
    """Minimum-cost-flow settlement over already-computed balances.

    Every edge costs the same, so the objective is the total amount moved, not
    the number of transfers -- on a complete graph that total is a constant for
    any direct debtor-to-creditor routing, and the cost only penalises routing
    through an intermediary. What bounds the transfer count is ``network_simplex``
    returning a basic solution, whose support is a spanning tree: at most
    ``n - 1`` transfers. Usually optimal, never guaranteed to be.

    Raises ``networkx.NetworkXUnfeasible`` if the balances do not sum to zero.
    """
    graph = nx.DiGraph()
    for person_id, balance in balances.items():
        graph.add_node(person_id, demand=balance)

    graph.add_weighted_edges_from(pair + (1,) for pair in itertools.permutations(people, 2))

    _flow_cost, flow_dict = nx.network_simplex(graph)
    return flow_dict


def solve_mincost_problem_for_expenses(expenses, people, settlements=None):
    """Settle ``expenses``, less any payments already recorded in ``settlements``.

    ``expenses`` is a list of dicts shaped like::

        {
            'whopaid': [{'personId': <id>, 'amount': Fraction(...)}, ...],
            'whoshouldpay': {<personId>: Fraction(...) | None, ...},
        }

    A ``None`` share means "split the remainder of this expense evenly among
    everyone with a ``None`` share". ``settlements`` is a list of dicts shaped
    like ``{'from': <id>, 'to': <id>, 'amount': Fraction(...)}``.

    Raises ``networkx.NetworkXUnfeasible`` if the supplied shares are
    inconsistent (don't sum to the paid total); see ``force_feasible`` for a
    workaround.
    """
    balances = compute_balances(expenses, people)
    if settlements:
        balances = apply_settlements(balances, settlements)
    return solve_from_balances(balances, people)
