from decimal import Decimal
from fractions import Fraction

from django.test import TestCase
from networkx import NetworkXUnfeasible

from netbox_ledger_tracker.calc.basic import basic_calc
from netbox_ledger_tracker.calc.matrix import result_to_matrix
from netbox_ledger_tracker.calc.mincost import force_feasible, solve_mincost_problem_for_expenses


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
        # the synthetic person absorbs the imbalance; the real people's mutual debt is unaffected
        self.assertEqual(result[61][60], Fraction(1, 3))
        self.assertEqual(result[60][61], 0)


class ResultToMatrixTest(TestCase):
    def test_matrix_includes_totals(self):
        people = {1: 'Alice', 2: 'Bob'}
        matrix = result_to_matrix({2: {1: 50}}, people)
        self.assertEqual(matrix[1][2], 50)
        self.assertEqual(matrix[1]['total'], 50)
        self.assertEqual(matrix['total'][2], 50)
        self.assertEqual(matrix[2][1], Decimal(0))
