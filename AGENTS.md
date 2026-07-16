# NetBox Ledger Tracker

## Repository Overview

NetBox Ledger Tracker is a NetBox plugin for splitting shared expenses and
settling group debts — a NetBox-native port of
[buddyledger](https://github.com/tykling/buddyledger)'s domain model and
settlement algorithms. It is a single-package Django app installed into an
existing NetBox deployment, not a standalone application.

This file is the working guide for agents and contributors: layout, commands,
testing, and conventions.

## Tech Stack

- Python 3.12+ / Django (as bundled with NetBox) / Django REST Framework
- Targets **NetBox 4.5.x** (`>=4.5.0,<4.6.0`, see [netbox-plugin.yaml](netbox-plugin.yaml)
  and [pyproject.toml](pyproject.toml))
- GraphQL via Strawberry / strawberry-django (`schema` is a list, see
  [netbox_ledger_tracker/graphql/__init__.py](netbox_ledger_tracker/graphql/__init__.py))
- django-tables2 for list views, django-filter for filtering
- `networkx` for the optimized (minimum-cost-flow) settlement algorithm
- Packaging via setuptools-scm dynamic versioning
  ([pyproject.toml](pyproject.toml)); lint and format via ruff, mirroring
  NetBox Core; type-checking via pyright (basic)

## Repository Map

```text
.
├── netbox_ledger_tracker/          — the plugin Django app
│   ├── __init__.py                 — PluginConfig, default_settings, ready(),
│   │                                  plugin-settings validation
│   ├── version.py                  — __version__ from package metadata
│   ├── choices.py                  — ChoiceSet subclasses (incl. LedgerCalcMethodChoices)
│   ├── models.py                   — Currency, Ledger, Person, Expense, ExpensePart
│   ├── calc/                       — framework-free settlement engine
│   │   ├── basic.py                — pairwise debt netting
│   │   ├── mincost.py              — minimum-cost-flow settlement (networkx)
│   │   ├── matrix.py               — payer x receiver debt matrix
│   │   └── currency.py             — currency conversion helpers
│   ├── filtersets.py               — NetBoxModelFilterSet subclasses
│   ├── forms.py                    — model forms + ExpenseSplitForm
│   ├── tables.py                   — NetBoxTable definitions
│   ├── views.py                    — CRUD views + ExpenseSplitView, LedgerSettleUpView
│   ├── urls.py                     — UI URL routes
│   ├── navigation.py               — PluginMenu / menu items
│   ├── search.py                   — SearchIndex registrations
│   ├── ui/panels.py                — ObjectAttributesPanel definitions
│   ├── management/commands/        — get_ledger_currency_rates
│   ├── api/                        — serializers.py, views.py, urls.py
│   ├── graphql/                    — __init__.py (schema = [LedgerTrackerQuery]),
│   │                                  schema.py, types.py, filters.py
│   ├── migrations/                 — Django migrations
│   ├── templates/netbox_ledger_tracker/ — currency/ledger/person/expense/settle-up templates
│   └── tests/                      — test_models.py, test_calc.py, test_filtersets.py,
│                                      test_forms.py, test_views.py
├── pyproject.toml                  — packaging metadata (setuptools-scm) + ruff/pyright config
├── netbox-plugin.yaml              — NetBox compatibility declaration
├── MANIFEST.in                     — include templates/static/fixtures in sdists
├── README.md / CHANGELOG.md
├── scripts/release_changelog_tag.py
└── .gitignore
```

## Commands

All commands run from a NetBox checkout's `netbox/` directory with the plugin
installed (editable) and enabled in `PLUGINS`. There is no Makefile.

| Command | What it does |
|---|---|
| `pip install -e .` | Install the plugin editable into the NetBox venv |
| `python manage.py makemigrations netbox_ledger_tracker` | Generate migrations after model changes |
| `python manage.py makemigrations --check` | Verify migrations are up to date |
| `python manage.py migrate netbox_ledger_tracker` | Apply migrations |
| `python manage.py test netbox_ledger_tracker` | Run the plugin test suite |
| `python manage.py get_ledger_currency_rates` | Fetch exchange rates from `currency_rate_feed_url` |

## Development Setup

1. Activate the NetBox virtualenv.
2. `pip install -e .` from this repository.
3. Add `netbox_ledger_tracker` to `PLUGINS` (and optionally `PLUGINS_CONFIG`)
   in NetBox `configuration.py`.
4. From `netbox/`, run `makemigrations --check`, `migrate`, then `runserver`.

## Testing

Tests use `django.test.TestCase` (not pytest) and run under NetBox's test
runner, except `test_calc.py` which has no NetBox/Django dependency. Set
`NETBOX_CONFIGURATION` first:

```bash
export NETBOX_CONFIGURATION=netbox.configuration_testing
python manage.py test netbox_ledger_tracker
```

| Module | Coverage area |
|---|---|
| `test_models.py` | Model methods, validation, constraints |
| `test_calc.py` | Settlement algorithms, verified against buddyledger's own worked examples — no NetBox/Django imports |
| `test_filtersets.py` | FilterSet fields and query behavior |
| `test_forms.py` | Form validation, incl. `ExpenseSplitForm` |
| `test_views.py` | UI views, incl. `ExpenseSplitView` / `LedgerSettleUpView` |

## Common Tasks

### Add a new model

1. Add the model to `models.py` inheriting from `NetBoxModel`.
2. Run `python manage.py makemigrations netbox_ledger_tracker` in a live
   NetBox env.
3. Wire the full surface: choices, filterset, forms, table, serializer,
   viewset, REST/UI URL routes, UI views, navigation, search index, GraphQL
   type/filter, and a detail template (or `ui/panels.py` panel).
4. Add tests (model, forms, views; `calc` changes need `test_calc.py` coverage).

### Change the settlement engine

`calc/` is intentionally framework-free (no Django/NetBox imports) so its
algorithms can be unit-tested directly against buddyledger's original worked
examples. Keep new settlement logic in `calc/` and call it from `models.py` /
`views.py` — don't let Django imports leak into `calc/`.

## Conventions and Patterns

- **Base class**: inherit `NetBoxModel`; explicit `get_absolute_url()` per model.
- **FK filters**: always add explicit `<field>_id` variants in FilterSets.
- **Serializers**: include a `url` field; use `nested=True` + `brief_fields`.
- **GraphQL**: `schema` must be a list — `schema = [LedgerTrackerQuery]`. The
  `graphql/` package `__init__` exports it; a sibling `graphql.py` would be
  shadowed by the package directory and must not exist.
- **Person is not a NetBox User**: `Person` is its own lightweight model
  scoped to a `Ledger`, with an optional nullable `user` FK — don't collapse
  the two.
- **Settlement engine**: `calc/` stays framework-free; see above.
- **Version pinning**: keep NetBox compatibility in sync across
  [netbox-plugin.yaml](netbox-plugin.yaml) and `netbox-plugin-development`
  metadata.

## Gotchas

- `schema` in `graphql/__init__.py` must remain a **list** of Strawberry query
  types — a bare `strawberry.Schema(...)` object will not register with
  NetBox's `extend()`.
- `calc/mincost.py` depends on `networkx`; don't add Django/NetBox imports to
  anything under `calc/` — its tests assert it stays dependency-free of both.
- Plugin settings (`base_currency`, `default_calc_method`,
  `currency_rate_feed_url`) are validated (with warnings, not hard failures)
  in `_validate_plugin_settings()` during `ready()` — extend that function
  when adding new settings rather than validating ad hoc at call sites.

## Preferred Skills

- For NetBox plugin-development guidance, prefer the official NetBox Labs
  skill set: <https://github.com/netboxlabs/skills> (e.g.
  `netbox-plugin-development`, `netbox-data-modeling`,
  `netbox-api-integration`) over ad hoc conventions.
- For scope and simplicity checks, prefer the `ponytail` skill:
  <https://github.com/DietrichGebert/ponytail> — invoke it when evaluating
  whether an implementation is minimal enough (YAGNI, no premature
  abstraction).

## References

- Usage, install, and plugin settings: [README.md](README.md)
- NetBox plugin development: <https://netboxlabs.com/docs/netbox/plugins/development/>
