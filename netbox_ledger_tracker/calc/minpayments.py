"""Settlement that actually minimises the number of transfers.

``mincost`` gives every edge the same weight, so its objective is the total
amount moved -- which on a complete graph is a constant for any direct
debtor-to-creditor routing. It is therefore indifferent to how many transfers it
uses, and only avoids routing through intermediaries. The count is bounded
incidentally, by ``network_simplex`` returning a basic solution whose support is
a spanning tree: at most ``n - 1`` transfers.

Fewer is often possible. Balances ``A:+10, B:-10, C:+10, D:-10`` settle in two
payments, but ``n - 1`` is three and nothing in the cost function prefers the
smaller answer. The gain comes from spotting subgroups that already net to zero
and settling each in isolation: ``k`` people need ``k - 1`` transfers, so more
groups means fewer payments overall.

Finding that partition is NP-hard -- it is subset-sum in disguise -- so the exact
search is capped and falls back to the minimum-cost solver above the limit.
"""

from .balances import apply_settlements, compute_balances
from .mincost import solve_from_balances

__all__ = (
    'DEFAULT_MAX_EXACT_PEOPLE',
    'partition_zero_sum',
    'solve_min_payments',
    'solve_min_payments_for_expenses',
)

# 3^n submask enumeration: 12 people is ~531k steps and imperceptible; 20 would
# be ~3.5 billion. Anything larger falls back rather than hanging the page.
DEFAULT_MAX_EXACT_PEOPLE = 12


def partition_zero_sum(balances):
    """Split ``{person_id: amount}`` into as many zero-sum groups as possible.

    Returns a list of lists of person ids. Every group sums to zero, so it can be
    settled without any money crossing a group boundary. The whole input always
    sums to zero, so there is always at least one valid answer: the single group
    containing everyone.

    Exact, via subset-sum dynamic programming over bitmasks -- O(3^n). Callers
    are responsible for keeping ``n`` small; see ``solve_min_payments``.
    """
    ids = list(balances)
    count = len(ids)
    if not count:
        return []

    values = [balances[person_id] for person_id in ids]
    full = (1 << count) - 1

    # Sum of every subset, built by peeling off the lowest set bit.
    subset_sum = [0] * (1 << count)
    for mask in range(1, 1 << count):
        lowest = (mask & -mask).bit_length() - 1
        subset_sum[mask] = subset_sum[mask ^ (1 << lowest)] + values[lowest]

    # best[mask] = most zero-sum groups `mask` can be split into, -1 if it cannot.
    best = [-1] * (1 << count)
    chosen = [0] * (1 << count)
    best[0] = 0

    for mask in range(1, 1 << count):
        lowest_bit = mask & -mask
        # Enumerate submasks containing the lowest set bit, so each group is
        # considered exactly once rather than in every possible order.
        submask = mask
        while submask:
            if submask & lowest_bit and subset_sum[submask] == 0 and best[mask ^ submask] >= 0:
                candidate = best[mask ^ submask] + 1
                if candidate > best[mask]:
                    best[mask] = candidate
                    chosen[mask] = submask
            submask = (submask - 1) & mask

    groups = []
    mask = full
    while mask:
        submask = chosen[mask]
        groups.append([ids[index] for index in range(count) if submask & (1 << index)])
        mask ^= submask

    return groups


def solve_min_payments(balances, people, max_exact_people=None):
    """Settle ``balances`` using as few transfers as possible.

    Falls back to the minimum-cost solver when more people carry a non-zero
    balance than ``max_exact_people``, since the exact partition is exponential.
    People already square with the group are dropped: they need no transfer, and
    excluding them shrinks the search.
    """
    outstanding = {person_id: amount for person_id, amount in balances.items() if amount != 0}
    if not outstanding:
        return {}

    limit = DEFAULT_MAX_EXACT_PEOPLE if max_exact_people is None else max_exact_people
    if len(outstanding) > limit:
        return solve_from_balances(balances, people)

    result = {}
    for group in partition_zero_sum(outstanding):
        group_balances = {person_id: outstanding[person_id] for person_id in group}
        for payer, receivers in solve_from_balances(group_balances, group).items():
            result.setdefault(payer, {}).update(receivers)

    return result


def solve_min_payments_for_expenses(expenses, people, settlements=None, max_exact_people=None):
    """``solve_min_payments`` over expenses, less any payments already recorded."""
    balances = compute_balances(expenses, people)
    if settlements:
        balances = apply_settlements(balances, settlements)
    return solve_min_payments(balances, people, max_exact_people=max_exact_people)
