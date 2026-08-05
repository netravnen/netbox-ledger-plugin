"""Unit tests for global search index registrations in netbox_ledger_tracker."""

from netbox.search.backends import search_backend
from utilities.testing import TestCase

from netbox_ledger_tracker.models import Currency, Ledger, Person


class SearchIndexTest(TestCase):
    def test_search_ledger_models(self):
        currency = Currency.objects.create(iso4217_code='USD', base_rate=1.0)
        ledger = Ledger.objects.create(name='Conference Trip 2026', currency=currency)
        person = Person.objects.create(name='Alice Smith')

        results = search_backend.search('Conference', user=None)
        results_qs = [res.object for res in results]
        self.assertIn(ledger, results_qs)
