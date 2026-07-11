# NetBox Ledger Tracker

NetBox plugin for splitting shared expenses and settling group debts — a NetBox-native port of [buddyledger](https://github.com/tykling/buddyledger)'s domain model and settlement algorithms.

## What This Plugin Provides

- **Ledgers**: a named pool of shared expenses in one currency (e.g. a trip, or a running house tab)
- **People**: lightweight, per-ledger participants, optionally linked to a NetBox user account
- **Expenses**: who paid what, and who owes what share — supporting a mix of fixed shares and an automatic even split of the remainder
- Two settlement algorithms per ledger: **basic** (pairwise debt netting) and **optimized** (minimum-cost-flow settlement via `networkx`, minimizing the number of payments needed)
- A **Split Expense** screen that creates/edits an expense and its full per-person breakdown in one submission
- A **Settle Up** view rendering a payer x receiver debt matrix
- NetBox UI, REST API, GraphQL, search indexes, and a `get_ledger_currency_rates` management command for fetching exchange rates

## Repository Layout

Plugin package: [netbox_ledger_tracker/](netbox_ledger_tracker/)

- `models.py` — Currency, Ledger, Person, Expense, ExpensePart
- `calc/` — pure-Python settlement engine (`basic.py`, `mincost.py`, `matrix.py`, `currency.py`), independently unit-tested with no NetBox/Django dependency
- `views.py` — standard CRUD views plus the custom `ExpenseSplitView` and `LedgerSettleUpView`
- `forms.py` — includes `ExpenseSplitForm`, the dynamic per-person split form

## Compatibility

- Python: `>=3.12`
- NetBox target: `>=4.5.0,<4.6.0`

## Install In NetBox

Install into the existing NetBox virtual environment:

```bash
/opt/netbox/venv/bin/pip install --force-reinstall --no-cache-dir -U \
  git+https://github.com/netravnen/netbox-ledger-plugin.git@main
```

## Development (Quick Start)

Create and activate a virtual environment, install dependencies and this package in editable mode, then enable `netbox_ledger_tracker` in NetBox's plugin configuration.

## Plugin Settings

Optional settings under `PLUGINS_CONFIG['netbox_ledger_tracker']`:

- `base_currency`: ISO 4217 code new `Currency` rows are pegged against (default `"DKK"`).
- `default_calc_method`: default `Ledger.calc_method` for newly created ledgers, `"basic"` or `"optimized"` (default `"basic"`).
- `currency_rate_feed_url`: feed URL used by the `get_ledger_currency_rates` management command (default: Danmarks Nationalbank's XML feed, which publishes DKK-denominated rates).

## Design Notes

- **Person is not a NetBox User.** Buddyledger's use case is ad-hoc groups of participants (e.g. a weekend trip's guests) who usually aren't NetBox accounts, so `Person` is its own lightweight model scoped to a `Ledger`. An optional nullable `user` FK links a person to a real NetBox account when useful.
- **The settlement engine is framework-free.** `netbox_ledger_tracker/calc/` has no Django/NetBox imports and is verified against the original buddyledger algorithm's own worked examples in `tests/test_calc.py`.
