# NetBox Ledger Tracker

NetBox plugin for splitting shared expenses and settling group debts — a NetBox-native port of [buddyledger](https://github.com/tykling/buddyledger)'s domain model and settlement algorithms.

## What This Plugin Provides

- **Ledgers**: a named pool of shared expenses in one currency (e.g. a trip, or a running house tab)
- **People**: lightweight, per-ledger participants, optionally linked to a NetBox user account
- **Expenses**: who paid what, and who owes what share — supporting a mix of fixed shares and an automatic even split of the remainder
- Three settlement algorithms per ledger:
  - **basic** — pairwise debt netting
  - **optimized** — minimum-cost-flow settlement via `networkx`. Minimises the total amount moved, which yields at most `n - 1` transfers; often the fewest possible, but not guaranteed
  - **minimal** — fewest transfers. Splits the group into subsets that already net to zero and settles each in isolation. The search is exponential, so it is capped by `minimal_max_people` and falls back to **optimized** above that
- **Settlements**: record a payment that has actually been made between two people, in any currency, and see it deducted from what is still outstanding
- Per-person **balances** (paid / share / settled / net) on the ledger page and above the Settle Up matrix, computed from the same figures as the matrix itself
- A **Split Expense** screen that creates/edits an expense and its full per-person breakdown in one submission
- A **Settle Up** view rendering a payer x receiver debt matrix
- NetBox UI, REST API, GraphQL, search indexes, and a `get_ledger_currency_rates` management command for fetching exchange rates

## Repository Layout

Plugin package: [netbox_ledger_tracker/](netbox_ledger_tracker/)

- `models.py` — Currency, Ledger, Person, Expense, ExpensePart, Settlement
- `calc/` — pure-Python settlement engine (`balances.py`, `basic.py`, `mincost.py`, `minpayments.py`, `matrix.py`, `currency.py`), independently unit-tested with no NetBox/Django dependency
- `summary.py` — the single place that turns ledger rows into calculator input, shared by the Settle Up matrix and the balance tables so the two cannot disagree
- `views.py` — standard CRUD views plus the custom `ExpenseSplitView` and `LedgerSettleUpView`
- `forms.py` — includes `ExpenseSplitForm`, the dynamic per-person split form

## Compatibility

- Python: `>=3.12`
- NetBox target: `>=4.6.4,<4.7.0`

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
- `default_calc_method`: default `Ledger.calc_method` for newly created ledgers, `"basic"`, `"optimized"` or `"minimal"` (default `"basic"`).
- `minimal_max_people`: cap on the exact search used by the `"minimal"` method (default `12`). The partition search is `O(3^n)`, so a ledger with more than this many people carrying a non-zero balance falls back to `"optimized"` and says so on the Settle Up page.
- `currency_rate_feed_url`: feed URL used by the `get_ledger_currency_rates` management command (default: Danmarks Nationalbank's XML feed, which publishes DKK-denominated rates).

## Design Notes

- **Person is not a NetBox User.** Buddyledger's use case is ad-hoc groups of participants (e.g. a weekend trip's guests) who usually aren't NetBox accounts, so `Person` is its own lightweight model scoped to a `Ledger`. An optional nullable `user` FK links a person to a real NetBox account when useful.
- **The settlement engine is framework-free.** `netbox_ledger_tracker/calc/` has no Django/NetBox imports and is verified against the original buddyledger algorithm's own worked examples in `tests/test_calc.py`.
