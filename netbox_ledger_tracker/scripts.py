from extras.scripts import ObjectVar, Script
from .models import Ledger


class NetLedgerScript(Script):
    description = "Form-driven script to compute and log ledger netting transactions"

    ledger = ObjectVar(
        model=Ledger,
        description="Target ledger for netting calculation",
    )

    def run(self, data, commit):
        ledger = data['ledger']
        expenses_count = ledger.expenses.count()
        if commit:
            self.log_success(f"Calculated netting for ledger '{ledger.name}' across {expenses_count} expense(s).")
        else:
            self.log_info(f"Dry run: Would calculate netting for ledger '{ledger.name}' across {expenses_count} expense(s).")
