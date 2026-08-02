# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added

- **Settlements.** A new `Settlement` model records a payment actually made
  between two people, so a debt that has been paid stops being reported.
  Previously the Settle Up matrix kept showing the original debt no matter
  what had changed hands, and the only workaround was inventing a
  compensating expense that never happened. Settlements carry their own
  currency, because people settle in whatever they have to hand. Full CRUD,
  REST and GraphQL surfaces, and both settlement algorithms deduct them.
- **Per-person balances** (paid / share / settled / net) on the ledger page
  and above the Settle Up matrix, derived from the same figures as the
  matrix so the two cannot disagree.
- **A third `calc_method`, `minimal`**, which genuinely minimises the number
  of transfers by settling subgroups that already net to zero in isolation.
  The search is exponential, so it is capped by the new `minimal_max_people`
  setting (default 12) and falls back to `optimized` above that, saying so
  on the page. Measured over 400 random balance sets of 4-8 people, it used
  strictly fewer transfers than `optimized` in 15% of cases and never more.
- `Expense.fx_rate`, recording the exchange rate an expense was priced at, so
  later rate updates cannot re-price it.

### Fixed

- **Currency conversion now happens on every write path.** It previously
  lived in the Split Expense view alone, so the standard Add Expense form,
  Clone, and the REST API all raised `IntegrityError` (a hard HTTP 500) by
  failing to set the not-null `amount_native`, while bulk import stored the
  raw amount unconverted and silently corrupted the settlement maths for
  cross-currency expenses. Conversion is now derived by the model.
- **Exchange rates are frozen per expense.** `amount_native` used to be
  recomputed from whatever `Currency.base_rate` happened to hold, so running
  `get_ledger_currency_rates` re-priced historical expenses and changed
  figures people had already settled on.
- `amount_native`, `fx_rate`, `has_paid_native` and `should_pay_native` are
  read-only over the REST API; they are derived, and honouring a supplied
  value let the API contradict the maths.
- The `optimized` method was documented as minimising the number of
  payments. It does not: with uniform edge weights the objective is the
  total amount moved, and the transfer count is merely bounded at `n - 1`.
  The documentation now says what it actually does, and `minimal` provides
  the behaviour that was described.

### Upgrade notes

- Migration `0003` backfills `fx_rate` from the currencies each expense
  references and restates `amount_native` and the per-part amounts to match,
  repairing rows the old bulk import path stored unconverted.

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
