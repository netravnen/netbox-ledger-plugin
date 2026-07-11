import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import netbox_ledger_tracker.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict)),
                (
                    'iso4217_code',
                    models.CharField(
                        max_length=3,
                        unique=True,
                        validators=[netbox_ledger_tracker.models.validate_iso4217_code],
                        verbose_name='ISO 4217 code',
                    ),
                ),
                (
                    'base_rate',
                    models.DecimalField(
                        decimal_places=6,
                        max_digits=20,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                ('comments', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'Currency',
                'verbose_name_plural': 'Currencies',
                'ordering': ['iso4217_code'],
            },
        ),
        migrations.CreateModel(
            name='Ledger',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict)),
                ('name', models.CharField(max_length=100)),
                ('closed', models.BooleanField(default=False)),
                (
                    'calc_method',
                    models.CharField(
                        choices=[
                            ('basic', 'Basic (pairwise netting)'),
                            ('optimized', 'Optimized (minimum-cost settlement)'),
                        ],
                        default=netbox_ledger_tracker.models._default_calc_method,
                        max_length=20,
                    ),
                ),
                ('comments', models.TextField(blank=True)),
                (
                    'currency',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='ledgers',
                        to='netbox_ledger_tracker.currency',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Ledger',
                'verbose_name_plural': 'Ledgers',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict)),
                ('name', models.CharField(max_length=100)),
                (
                    'ledger',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='people',
                        to='netbox_ledger_tracker.ledger',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='ledger_people',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Person',
                'verbose_name_plural': 'People',
                'ordering': ['ledger', 'name'],
                'unique_together': {('ledger', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict)),
                ('name', models.CharField(max_length=100)),
                (
                    'amount',
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=20,
                        validators=[django.core.validators.MinValueValidator(0.01)],
                    ),
                ),
                ('amount_native', models.DecimalField(decimal_places=2, editable=False, max_digits=20)),
                ('date', models.DateField()),
                ('comments', models.TextField(blank=True)),
                (
                    'currency',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='expenses',
                        to='netbox_ledger_tracker.currency',
                    ),
                ),
                (
                    'ledger',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='expenses',
                        to='netbox_ledger_tracker.ledger',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Expense',
                'verbose_name_plural': 'Expenses',
                'ordering': ['-date', '-pk'],
            },
        ),
        migrations.CreateModel(
            name='ExpensePart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict)),
                ('has_paid', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('has_paid_native', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('should_pay', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('should_pay_native', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('auto_amount', models.BooleanField(default=False)),
                (
                    'expense',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='parts',
                        to='netbox_ledger_tracker.expense',
                    ),
                ),
                (
                    'person',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='expense_parts',
                        to='netbox_ledger_tracker.person',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Expense Part',
                'verbose_name_plural': 'Expense Parts',
                'ordering': ['expense', 'person'],
                'unique_together': {('expense', 'person')},
            },
        ),
        migrations.AddField(
            model_name='expense',
            name='people',
            field=models.ManyToManyField(
                related_name='expenses',
                through='netbox_ledger_tracker.ExpensePart',
                to='netbox_ledger_tracker.person',
            ),
        ),
    ]
