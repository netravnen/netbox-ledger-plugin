"""REST API unit tests for netbox_ledger_tracker."""

from utilities.testing import APITestCase

from netbox_ledger_tracker.models import Currency, Ledger, Person


class CurrencyAPITest(APITestCase):
    def setUpTestData(cls):
        Currency.objects.create(iso4217_code='EUR', base_rate=1.0)
        Currency.objects.create(iso4217_code='USD', base_rate=1.08)

    def test_list_currencies(self):
        url = '/api/plugins/netbox-ledger-tracker/currencies/'
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)
