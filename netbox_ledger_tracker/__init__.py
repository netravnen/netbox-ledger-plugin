import logging

from django.conf import settings as django_settings
from netbox.plugins import PluginConfig

from .version import __version__

LOGGER = logging.getLogger(__name__)


class LedgerTrackerConfig(PluginConfig):
    name = 'netbox_ledger_tracker'
    verbose_name = 'Ledger Tracker'
    description = 'Split shared expenses and settle group debts in NetBox'
    version = __version__
    author = 'ch'
    author_email = 'netbox-ledger-tracker@btwlf.eu'
    base_url = 'ledger'
    default_settings = {
        # ISO 4217 code new Currency rows are pegged against by default.
        'base_currency': 'DKK',
        # Default Ledger.calc_method for newly created ledgers.
        'default_calc_method': 'basic',
        # Feed used by the get_ledger_currency_rates management command.
        'currency_rate_feed_url': 'https://www.nationalbanken.dk/_vti_bin/DN/DataService.svc/CurrencyRatesXML?lang=da',
    }

    @classmethod
    def _validate_plugin_settings(cls):
        plugin_config = getattr(django_settings, 'PLUGINS_CONFIG', {}).get('netbox_ledger_tracker', {})
        if not isinstance(plugin_config, dict):
            LOGGER.warning(
                "PLUGINS_CONFIG['netbox_ledger_tracker'] must be a mapping; got %s",
                type(plugin_config).__name__,
            )
            return

        from .choices import LedgerCalcMethodChoices

        allowed_calc_methods = {code for code, _label, _color in LedgerCalcMethodChoices.CHOICES}

        base_currency = plugin_config.get('base_currency')
        if base_currency is not None:
            normalized = str(base_currency).strip().upper()
            if len(normalized) != 3 or not normalized.isalpha():
                LOGGER.warning(
                    'Invalid netbox_ledger_tracker.base_currency=%r; expected a 3-letter ISO 4217 code',
                    base_currency,
                )

        default_calc_method = plugin_config.get('default_calc_method')
        if default_calc_method is not None and default_calc_method not in allowed_calc_methods:
            LOGGER.warning(
                'Invalid netbox_ledger_tracker.default_calc_method=%r; expected one of LedgerCalcMethodChoices',
                default_calc_method,
            )

    def ready(self):
        super().ready()
        self._validate_plugin_settings()


config = LedgerTrackerConfig
