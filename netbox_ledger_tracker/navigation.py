from netbox.choices import ButtonColorChoices
from netbox.plugins.navigation import PluginMenu, PluginMenuButton, PluginMenuItem

menu = PluginMenu(
    label='Ledger Tracker',
    groups=(
        (
            'Ledgers',
            (
                PluginMenuItem(
                    link='plugins:netbox_ledger_tracker:ledger_list',
                    link_text='Ledgers',
                    permissions=['netbox_ledger_tracker.view_ledger'],
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_ledger_tracker:ledger_add',
                            title='Add',
                            icon_class='mdi mdi-plus-thick',
                            color=ButtonColorChoices.GREEN,
                            permissions=['netbox_ledger_tracker.add_ledger'],
                        ),
                        PluginMenuButton(
                            link='plugins:netbox_ledger_tracker:ledger_bulk_import',
                            title='Import',
                            icon_class='mdi mdi-upload',
                            color=ButtonColorChoices.BLUE,
                            permissions=['netbox_ledger_tracker.add_ledger'],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link='plugins:netbox_ledger_tracker:currency_list',
                    link_text='Currencies',
                    permissions=['netbox_ledger_tracker.view_currency'],
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_ledger_tracker:currency_add',
                            title='Add',
                            icon_class='mdi mdi-plus-thick',
                            color=ButtonColorChoices.GREEN,
                            permissions=['netbox_ledger_tracker.add_currency'],
                        ),
                        PluginMenuButton(
                            link='plugins:netbox_ledger_tracker:currency_bulk_import',
                            title='Import',
                            icon_class='mdi mdi-upload',
                            color=ButtonColorChoices.BLUE,
                            permissions=['netbox_ledger_tracker.add_currency'],
                        ),
                    ),
                ),
            ),
        ),
        (
            'Expenses',
            (
                PluginMenuItem(
                    link='plugins:netbox_ledger_tracker:settlement_list',
                    link_text='Settlements',
                    permissions=['netbox_ledger_tracker.view_settlement'],
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_ledger_tracker:settlement_add',
                            title='Add',
                            icon_class='mdi mdi-plus-thick',
                            color=ButtonColorChoices.GREEN,
                            permissions=['netbox_ledger_tracker.add_settlement'],
                        ),
                        PluginMenuButton(
                            link='plugins:netbox_ledger_tracker:settlement_bulk_import',
                            title='Import',
                            icon_class='mdi mdi-upload',
                            color=ButtonColorChoices.BLUE,
                            permissions=['netbox_ledger_tracker.add_settlement'],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link='plugins:netbox_ledger_tracker:expense_list',
                    link_text='Expenses',
                    permissions=['netbox_ledger_tracker.view_expense'],
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_ledger_tracker:expense_split_add',
                            title='Split Expense',
                            icon_class='mdi mdi-call-split',
                            color=ButtonColorChoices.GREEN,
                            permissions=['netbox_ledger_tracker.add_expense'],
                        ),
                        PluginMenuButton(
                            link='plugins:netbox_ledger_tracker:expense_bulk_import',
                            title='Import',
                            icon_class='mdi mdi-upload',
                            color=ButtonColorChoices.BLUE,
                            permissions=['netbox_ledger_tracker.add_expense'],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link='plugins:netbox_ledger_tracker:person_list',
                    link_text='People',
                    permissions=['netbox_ledger_tracker.view_person'],
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_ledger_tracker:person_add',
                            title='Add',
                            icon_class='mdi mdi-plus-thick',
                            color=ButtonColorChoices.GREEN,
                            permissions=['netbox_ledger_tracker.add_person'],
                        ),
                        PluginMenuButton(
                            link='plugins:netbox_ledger_tracker:person_bulk_import',
                            title='Import',
                            icon_class='mdi mdi-upload',
                            color=ButtonColorChoices.BLUE,
                            permissions=['netbox_ledger_tracker.add_person'],
                        ),
                    ),
                ),
            ),
        ),
    ),
    icon_class='mdi mdi-cash-multiple',
)
