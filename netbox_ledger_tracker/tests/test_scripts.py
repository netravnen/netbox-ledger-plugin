"""Unit tests for custom automation scripts in netbox_ledger_tracker."""

from utilities.testing import TestCase

from netbox_ledger_tracker.models import Currency, Ledger
from netbox_ledger_tracker.scripts import NetLedgerScript


class ScriptsTest(TestCase):
    def test_net_ledger_script_dry_run_and_commit(self):
        currency = Currency.objects.create(iso4217_code='EUR', base_rate=1.0)
        ledger = Ledger.objects.create(name='Vacation 2026', currency=currency)

        script = NetLedgerScript()

        # Dry run execution (commit=False)
        script.run({'ledger': ledger}, commit=False)

        # Commit execution (commit=True)
        script.run({'ledger': ledger}, commit=True)
