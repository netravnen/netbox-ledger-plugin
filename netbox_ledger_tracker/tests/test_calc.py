from decimal import Decimal
from fractions import Fraction

from django.test import TestCase
from networkx import NetworkXUnfeasible

from netbox_ledger_tracker.calc.balances import apply_settlements, compute_balances
from netbox_ledger_tracker.calc.basic import basic_calc
from netbox_ledger_tracker.calc.matrix import result_to_matrix
from netbox_ledger_tracker.calc.mincost import (
    force_feasible,
    solve_from_balances,
    solve_mincost_problem_for_expenses,
)
from netbox_ledger_tracker.calc.minpayments import (
    partition_zero_sum,
    solve_min_payments,
    solve_min_payments_for_expenses,
)

# One person covers a 100 dinner split evenly: person 2 ends up owing person 1 fifty.
DINNER = [
    {
        'whopaid': [{'personId': 1, 'amount': Fraction(100)}],
        'whoshouldpay': {1: Fraction(50), 2: Fraction(50)},
    }
]


class ComputeBalancesTest(TestCase):
    def test_balances_are_signed_net_positions(self):
        balances = compute_balances(DINNER, [1, 2])
        self.assertEqual(balances[1], Fraction(50))
        self.assertEqual(balances[2], Fraction(-50))

    def test_balances_sum_to_zero(self):
        balances = compute_balances(DINNER, [1, 2])
        self.assertEqual(sum(balances.values()), 0)

    def test_auto_share_splits_the_remainder(self):
        expenses = [
            {
                'whopaid': [{'personId': 1, 'amount': Fraction(90)}],
                'whoshouldpay': {1: Fraction(30), 2: None, 3: None},
            }
        ]
        balances = compute_balances(expenses, [1, 2, 3])
        self.assertEqual(balances[1], Fraction(60))
        self.assertEqual(balances[2], Fraction(-30))
        self.assertEqual(balances[3], Fraction(-30))


class ApplySettlementsTest(TestCase):
    def test_settlement_moves_both_balances(self):
        balances = compute_balances(DINNER, [1, 2])
        adjusted = apply_settlements(balances, [{'from': 2, 'to': 1, 'amount': Fraction(50)}])
        self.assertEqual(adjusted[1], 0)
        self.assertEqual(adjusted[2], 0)

    def test_partial_settlement_leaves_the_remainder(self):
        balances = compute_balances(DINNER, [1, 2])
        adjusted = apply_settlements(balances, [{'from': 2, 'to': 1, 'amount': Fraction(20)}])
        self.assertEqual(adjusted[1], Fraction(30))
        self.assertEqual(adjusted[2], Fraction(-30))

    def test_overpayment_reverses_the_balance(self):
        balances = compute_balances(DINNER, [1, 2])
        adjusted = apply_settlements(balances, [{'from': 2, 'to': 1, 'amount': Fraction(80)}])
        self.assertEqual(adjusted[1], Fraction(-30))
        self.assertEqual(adjusted[2], Fraction(30))

    def test_does_not_mutate_the_input(self):
        balances = compute_balances(DINNER, [1, 2])
        apply_settlements(balances, [{'from': 2, 'to': 1, 'amount': Fraction(50)}])
        self.assertEqual(balances[1], Fraction(50))


class SettlementIntegrationTest(TestCase):
    """A recorded payment has to clear the debt under both algorithms."""

    def test_basic_full_settlement_clears_the_debt(self):
        debts = basic_calc(DINNER, [1, 2], settlements=[{'from': 2, 'to': 1, 'amount': Fraction(50)}])
        self.assertEqual(debts[2][1], 0)
        self.assertEqual(debts[1][2], 0)

    def test_basic_partial_settlement_leaves_the_remainder(self):
        debts = basic_calc(DINNER, [1, 2], settlements=[{'from': 2, 'to': 1, 'amount': Fraction(20)}])
        self.assertEqual(debts[2][1], Fraction(30))
        self.assertEqual(debts[1][2], 0)

    def test_basic_overpayment_flips_the_direction(self):
        debts = basic_calc(DINNER, [1, 2], settlements=[{'from': 2, 'to': 1, 'amount': Fraction(80)}])
        self.assertEqual(debts[1][2], Fraction(30))
        self.assertEqual(debts[2][1], 0)

    def test_optimized_full_settlement_clears_the_debt(self):
        result = solve_mincost_problem_for_expenses(
            DINNER, [1, 2], settlements=[{'from': 2, 'to': 1, 'amount': Fraction(50)}]
        )
        self.assertEqual(result[2][1], 0)
        self.assertEqual(result[1][2], 0)

    def test_optimized_partial_settlement_leaves_the_remainder(self):
        result = solve_mincost_problem_for_expenses(
            DINNER, [1, 2], settlements=[{'from': 2, 'to': 1, 'amount': Fraction(20)}]
        )
        self.assertEqual(result[2][1], Fraction(30))

    def test_no_settlements_matches_the_unsettled_result(self):
        self.assertEqual(basic_calc(DINNER, [1, 2]), basic_calc(DINNER, [1, 2], settlements=[]))


class MinPaymentsTest(TestCase):
    @staticmethod
    def _transfer_count(result):
        return sum(1 for receivers in result.values() for amount in receivers.values() if amount)

    def test_partitions_into_zero_sum_groups(self):
        balances = {'A': Fraction(10), 'B': Fraction(-10), 'C': Fraction(10), 'D': Fraction(-10)}
        groups = partition_zero_sum(balances)
        self.assertEqual(len(groups), 2)
        for group in groups:
            self.assertEqual(sum(balances[person] for person in group), 0)

    def test_falls_back_to_one_group_when_nothing_nets_out(self):
        balances = {'A': Fraction(30), 'B': Fraction(-10), 'C': Fraction(-10), 'D': Fraction(-10)}
        self.assertEqual(len(partition_zero_sum(balances)), 1)

    def test_uses_fewer_transfers_than_the_minimum_cost_solver(self):
        # Found by comparing the two solvers over random balances: {C, E} and
        # {A, B, D} each net to zero, so this settles in three transfers while
        # the minimum-cost solver spends four.
        balances = {
            'A': Fraction(-3),
            'B': Fraction(-38),
            'C': Fraction(20),
            'D': Fraction(41),
            'E': Fraction(-20),
        }
        people = list(balances)

        optimized = solve_from_balances(balances, people)
        minimal = solve_min_payments(balances, people)

        self.assertEqual(self._transfer_count(optimized), 4)
        self.assertEqual(self._transfer_count(minimal), 3)

    def test_settles_every_balance(self):
        balances = {
            'A': Fraction(-3),
            'B': Fraction(-38),
            'C': Fraction(20),
            'D': Fraction(41),
            'E': Fraction(-20),
        }
        result = solve_min_payments(balances, list(balances))

        # A person's balance is what flows in minus what flows out: someone owed
        # 41 must receive exactly 41, and someone owing 38 must send exactly 38.
        net = dict.fromkeys(balances, Fraction(0))
        for payer, receivers in result.items():
            for receiver, amount in receivers.items():
                net[payer] -= amount
                net[receiver] += amount
        for person, balance in balances.items():
            self.assertEqual(net[person], balance)

    def test_people_already_square_are_left_alone(self):
        balances = {'A': Fraction(10), 'B': Fraction(-10), 'C': Fraction(0)}
        result = solve_min_payments(balances, list(balances))
        self.assertNotIn('C', result)

    def test_nothing_to_do_when_everyone_is_settled(self):
        self.assertEqual(solve_min_payments({'A': Fraction(0), 'B': Fraction(0)}, ['A', 'B']), {})

    def test_falls_back_above_the_exact_search_limit(self):
        # Two obvious zero-sum pairs, but a limit of 3 forbids the exact search,
        # so this must return the minimum-cost answer rather than hang or fail.
        balances = {'A': Fraction(10), 'B': Fraction(-10), 'C': Fraction(10), 'D': Fraction(-10)}
        people = list(balances)

        result = solve_min_payments(balances, people, max_exact_people=3)

        self.assertEqual(result, solve_from_balances(balances, people))

    def test_settlements_are_netted_before_minimising(self):
        result = solve_min_payments_for_expenses(
            DINNER, [1, 2], settlements=[{'from': 2, 'to': 1, 'amount': Fraction(50)}]
        )
        self.assertEqual(self._transfer_count(result), 0)


class BasicCalcTest(TestCase):
    def test_simple_two_person_split(self):
        expenses = [
            {
                'whopaid': [{'personId': 1, 'amount': Fraction(100)}],
                'whoshouldpay': {1: Fraction(50), 2: Fraction(50)},
            }
        ]
        debts = basic_calc(expenses, [1, 2])
        self.assertEqual(debts[2][1], Fraction(50))
        self.assertEqual(debts[1][2], 0)

    def test_mutual_debts_are_netted(self):
        expenses = [
            {
                'whopaid': [{'personId': 'A', 'amount': Fraction(100)}],
                'whoshouldpay': {'A': Fraction(50), 'B': Fraction(50)},
            },
            {
                'whopaid': [{'personId': 'B', 'amount': Fraction(60)}],
                'whoshouldpay': {'A': Fraction(30), 'B': Fraction(30)},
            },
        ]
        debts = basic_calc(expenses, ['A', 'B'])
        # B owes A 50 from expense 1, A owes B 30 from expense 2 -> netted to B owes A 20
        self.assertEqual(debts['B']['A'], 20)
        self.assertEqual(debts['A']['B'], 0)


class MincostCalcTest(TestCase):
    def test_auto_split_share(self):
        # Two payers split a bill 50/50 automatically, a third person's share is fixed.
        result = solve_mincost_problem_for_expenses(
            [
                {
                    'whopaid': [
                        {'personId': 10, 'amount': Fraction(1, 2)},
                        {'personId': 11, 'amount': Fraction(1, 2)},
                    ],
                    'whoshouldpay': {10: None, 11: None, 12: Fraction(1, 2)},
                }
            ],
            [10, 11, 12],
        )
        self.assertEqual(
            result,
            {10: {11: Fraction(0, 1), 12: 0}, 11: {10: 0, 12: 0}, 12: {10: Fraction(1, 4), 11: Fraction(1, 4)}},
        )

    def test_explicit_none_share_participant(self):
        result = solve_mincost_problem_for_expenses(
            [{'whopaid': [{'personId': 60, 'amount': Fraction(1, 2)}], 'whoshouldpay': {60: Fraction(1, 6), 61: None}}],
            [61, 60],
        )
        self.assertEqual(result, {61: {60: Fraction(1, 3)}, 60: {61: 0}})

    def test_unbalanced_shares_raise_unfeasible(self):
        with self.assertRaises(NetworkXUnfeasible):
            solve_mincost_problem_for_expenses(
                [{'whopaid': [{'personId': 60, 'amount': Fraction(1, 2)}], 'whoshouldpay': {60: Fraction(1, 6)}}],
                [61, 60],
            )

    def test_force_feasible_recovers_from_unbalanced_shares(self):
        result = force_feasible(
            [{'whopaid': [{'personId': 60, 'amount': Fraction(1, 2)}], 'whoshouldpay': {60: Fraction(1, 6)}}],
            [61, 60],
        )
        # Person 60 paid 1/2 but was assigned a share of only 1/6, leaving 1/3
        # unaccounted for. The synthetic person absorbs exactly that, so the two
        # real people are left owing each other nothing -- person 61 is party to
        # neither the payment nor the split, so their balance is zero.
        self.assertEqual(result[61][60], 0)
        self.assertEqual(result[60][61], 0)

        (synthetic_id,) = [person_id for person_id in result if person_id not in (60, 61)]
        self.assertEqual(result[synthetic_id][60], Fraction(1, 3))


class ResultToMatrixTest(TestCase):
    def test_matrix_includes_totals(self):
        people = {1: 'Alice', 2: 'Bob'}
        matrix = result_to_matrix({2: {1: 50}}, people)
        self.assertEqual(matrix[1][2], 50)
        self.assertEqual(matrix[1]['total'], 50)
        self.assertEqual(matrix['total'][2], 50)
        self.assertEqual(matrix[2][1], Decimal(0))
