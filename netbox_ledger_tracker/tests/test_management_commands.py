"""Unit tests for CLI management commands in netbox_ledger_tracker."""

from django.core.management import call_command
from utilities.testing import TestCase

from netbox_ledger_tracker.models import Currency


class ManagementCommandsTest(TestCase):
    def test_get_ledger_currency_rates_command(self):
        Currency.objects.create(iso4217_code='DKK', base_rate=1.0)
        # Verify management command runs cleanly
        call_command('get_ledger_currency_rates')
