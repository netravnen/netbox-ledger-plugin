from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations, models

FX_RATE_QUANT = Decimal('0.0000000001')
MONEY_QUANT = Decimal('0.01')


def backfill_fx_rate(apps, schema_editor):
    """Give every existing expense the rate its currencies actually imply.

    Derived from Currency.base_rate rather than reconstructed from the stored
    amount_native. Reconstructing would faithfully reproduce the old bulk-import
    bug -- those rows hold an unconverted amount_native, which implies a rate of
    1 -- and there are no production deployments whose figures need preserving,
    so the correct value is simply better than the historical one.

    amount_native and the per-part amounts are restated to match, since leaving
    them would put the expense and its rate in disagreement.
    """
    Expense = apps.get_model('netbox_ledger_tracker', 'Expense')
    ExpensePart = apps.get_model('netbox_ledger_tracker', 'ExpensePart')

    for expense in Expense.objects.select_related('currency', 'ledger__currency').iterator():
        if expense.currency_id == expense.ledger.currency_id:
            rate = Decimal(1)
        else:
            rate = Decimal(expense.currency.base_rate) / Decimal(expense.ledger.currency.base_rate)
        rate = rate.quantize(FX_RATE_QUANT)

        Expense.objects.filter(pk=expense.pk).update(
            fx_rate=rate,
            amount_native=(Decimal(expense.amount) * rate).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP),
        )
        for part in ExpensePart.objects.filter(expense_id=expense.pk):
            ExpensePart.objects.filter(pk=part.pk).update(
                has_paid_native=(Decimal(part.has_paid) * rate).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP),
                should_pay_native=(Decimal(part.should_pay) * rate).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP),
            )


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
