from netbox.plugins import PluginTemplateExtension

from .version import __version__ as _plugin_version


class PluginVersionBadge(PluginTemplateExtension):
    models = [
        'netbox_ledger_tracker.currency',
        'netbox_ledger_tracker.ledger',
        'netbox_ledger_tracker.person',
        'netbox_ledger_tracker.expense',
        'netbox_ledger_tracker.expensepart',
        'netbox_ledger_tracker.settlement',
    ]

    def full_width_page(self):
        return self.render(
            'netbox_ledger_tracker/inc/plugin_version_badge.html',
            extra_context={'plugin_version': _plugin_version},
        )


template_extensions = [PluginVersionBadge]
