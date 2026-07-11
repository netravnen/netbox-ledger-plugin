"""Fetch currency exchange rates and update Currency.base_rate.

Ported from buddyledger's ``getcurrency`` command. The default feed
(Danmarks Nationalbank) publishes rates in DKK, so this command only
produces correct results when the plugin's configured ``base_currency``
is DKK (the default) — set ``PLUGINS_CONFIG['netbox_ledger_tracker']
['currency_rate_feed_url']`` to a different feed if you use another base.
"""

import xml.etree.ElementTree as ElementTree
from decimal import Decimal, InvalidOperation
from urllib.request import urlopen

from django.core.management.base import BaseCommand
from netbox.plugins import get_plugin_config

from ...models import Currency, validate_iso4217_code


class Command(BaseCommand):
    help = "Fetch currency exchange rates from the plugin's configured feed and update Currency.base_rate"

    def handle(self, *args, **options):
        base_currency = get_plugin_config('netbox_ledger_tracker', 'base_currency', 'DKK')
        feed_url = get_plugin_config('netbox_ledger_tracker', 'currency_rate_feed_url')

        if base_currency != 'DKK':
            self.stdout.write(
                self.style.WARNING(
                    f"base_currency is configured as '{base_currency}', but the default feed publishes rates "
                    'in DKK. Rates will be saved as-is; verify this is what you want, or configure a matching feed.'
                )
            )

        with urlopen(feed_url) as response:  # noqa: S310 -- feed URL is admin-configured, not user input
            xml_data = response.read()

        tree = ElementTree.fromstring(xml_data)
        for child in tree[0]:
            code = child.attrib.get('code', '')
            raw_rate = child.attrib.get('rate', '-')

            try:
                validate_iso4217_code(code.upper())
            except Exception:
                self.stdout.write(f'Skipping unrecognized currency code {code!r}')
                continue

            if raw_rate == '-':
                self.stdout.write(f'Skipping currency {code} - no rate published')
                continue

            try:
                rate = Decimal(raw_rate.replace('.', '').replace(',', '.')) / 100
            except InvalidOperation:
                self.stdout.write(f'Skipping currency {code} - could not parse rate {raw_rate!r}')
                continue

            self._save_rate(code.upper(), rate)

        # The base currency always prices at 1:1 against itself.
        self._save_rate(base_currency, Decimal('1'))
        self.stdout.write(self.style.SUCCESS('Done updating currency rates.'))

    def _save_rate(self, code, rate):
        currency, created = Currency.objects.update_or_create(
            iso4217_code=code,
            defaults={'base_rate': rate},
        )
        verb = 'Created' if created else 'Updated'
        self.stdout.write(f'{verb} {currency.iso4217_code}: 1 {currency.iso4217_code} = {rate} base units')
