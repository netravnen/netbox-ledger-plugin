# Changelog

All notable changes to this project will be documented in this file.

## 0.1.0 - 2026-07-12

### Added

- Initial release. A NetBox plugin for splitting shared expenses and
  settling group debts, mirroring the domain model and settlement
  algorithms of [buddyledger](https://github.com/tykling/buddyledger)
  onto NetBox's plugin scaffolding (models, forms, tables, filtersets,
  REST API, GraphQL, changelog/tags/custom-fields support).
- **Currency**, **Ledger**, **Person**, **Expense**, and **ExpensePart**
  models. A Ledger holds a group's shared expenses in one currency;
  Person is a lightweight, per-ledger participant optionally linked to a
  NetBox user account; Expense/ExpensePart record who paid what and who
  owes what share of each expense.
- Two settlement algorithms, selectable per-ledger via `calc_method`:
  - **Basic**: pairwise debt netting.
  - **Optimized**: a minimum-cost-flow settlement (via `networkx`) that
    minimizes the number of payments needed to settle every debt.
- A **Split Expense** screen (`netbox_ledger_tracker.views.ExpenseSplitView`)
  that creates or edits an Expense and its full per-person breakdown in one
  submission: each ledger member gets an "involved" checkbox plus
  paid/owed fields, with support for a mix of fixed shares and an
  automatic even split of whatever's left over (odd remainders are
  distributed cent-by-cent rather than lost to rounding).
- A **Settle Up** view (`netbox_ledger_tracker.views.LedgerSettleUpView`)
  that renders a payer x receiver debt matrix for a ledger using its
  configured calculation method.
- A `get_ledger_currency_rates` management command (ported from
  buddyledger's `getcurrency`) that fetches exchange rates from a
  configurable feed (defaults to Danmarks Nationalbank) and updates
  `Currency.base_rate`.
- Full REST API and GraphQL support for all five models.

### Backwards Compatibility

- N/A — initial release.
