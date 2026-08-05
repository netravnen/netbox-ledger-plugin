"""Unit tests for NetBox reports in netbox_ledger_tracker."""

from utilities.testing import TestCase

from netbox_ledger_tracker.models import Currency, Expense, Ledger
from netbox_ledger_tracker.reports import LedgerIntegrityReport


class ReportsTest(TestCase):
    def test_ledger_integrity_report(self):
        currency = Currency.objects.create(iso4217_code='EUR', base_rate=1.0)
        ledger = Ledger.objects.create(name='Trip 2026', currency=currency)
        expense = Expense.objects.create(ledger=ledger, description='Hotel', amount=100)

        report = LedgerIntegrityReport()
        report.test_ledger_currency()
        report.test_expense_splits()

        self.assertIn(ledger, report._log)
        self.assertIn(expense, report._log)
