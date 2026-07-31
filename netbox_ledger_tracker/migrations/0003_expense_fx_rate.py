from decimal import Decimal

from django.db import migrations, models

FX_RATE_QUANT = Decimal('0.0000000001')


def backfill_fx_rate(apps, schema_editor):
    """Derive each expense's frozen rate from the amounts already stored.

    Deliberately reconstructed from `amount_native / amount` rather than from the
    current `Currency.base_rate`. Rates move, so re-deriving from today's values
    would silently re-price historical expenses; and rows written by the old bulk
    import path stored an unconverted `amount_native`, which yields a rate of 1
    here. That preserves exactly what the ledger already reported instead of
    quietly changing settled figures. Operators who want those rows corrected can
    run the `ledger_recompute_fx` management command, which is opt-in per ledger.
    """
    Expense = apps.get_model('netbox_ledger_tracker', 'Expense')
    for expense in Expense.objects.all().iterator():
        if expense.amount and expense.amount != 0:
            rate = (Decimal(expense.amount_native) / Decimal(expense.amount)).quantize(FX_RATE_QUANT)
        else:
            rate = Decimal(1).quantize(FX_RATE_QUANT)
        Expense.objects.filter(pk=expense.pk).update(fx_rate=rate)


def noop(apps, schema_editor):
    """Reverse is a no-op: dropping the column discards the rates anyway."""


class Migration(migrations.Migration):
    dependencies = [
        ('netbox_ledger_tracker', '0002_currency_tags_expense_tags_expensepart_tags_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='fx_rate',
            field=models.DecimalField(decimal_places=10, max_digits=20, null=True),
        ),
        migrations.RunPython(backfill_fx_rate, noop),
        migrations.AlterField(
            model_name='expense',
            name='fx_rate',
            field=models.DecimalField(
                decimal_places=10,
                editable=False,
                help_text=(
                    'Ledger-currency units per unit of the expense currency. Frozen when the '
                    'expense is first saved, so later exchange-rate updates do not silently '
                    're-price historical expenses.'
                ),
                max_digits=20,
            ),
        ),
    ]
