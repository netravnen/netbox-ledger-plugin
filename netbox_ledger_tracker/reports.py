from extras.reports import Report
from .models import Expense, Ledger


class LedgerIntegrityReport(Report):
    description = "Audit ledger currency assignments and expense split completeness"

    def test_ledger_currency(self):
        for ledger in Ledger.objects.all():
            if not ledger.currency:
                self.log_failure(ledger, "Ledger has no currency set.")
            else:
                self.log_success(ledger)

    def test_expense_splits(self):
        for expense in Expense.objects.all():
            if not expense.parts.exists():
                self.log_warning(expense, "Expense has no split parts allocated to people.")
            else:
                self.log_success(expense)
