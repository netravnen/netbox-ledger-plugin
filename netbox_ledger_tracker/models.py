from decimal import Decimal

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel

from .choices import LedgerCalcMethodChoices

User = get_user_model()

validate_iso4217_code = RegexValidator(
    regex=r'^[A-Z]{3}$',
    message='Enter a valid ISO 4217 currency code (three uppercase letters, e.g. DKK, EUR, USD).',
)


def _default_calc_method() -> str:
    configured = django_settings.PLUGINS_CONFIG.get('netbox_ledger_tracker', {}).get('default_calc_method', 'basic')
    allowed = {code for code, _label, _color in LedgerCalcMethodChoices.CHOICES}
    return configured if configured in allowed else LedgerCalcMethodChoices.BASIC


class Currency(NetBoxModel):
    """An ISO 4217 currency, priced relative to the plugin's configured base currency."""

    clone_fields = ['base_rate']

    iso4217_code = models.CharField(
        max_length=3,
        unique=True,
        verbose_name='ISO 4217 code',
        validators=[validate_iso4217_code],
    )
    base_rate = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Price of one unit of this currency, expressed in the plugin base currency.',
    )
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ['iso4217_code']
        verbose_name = 'Currency'
        verbose_name_plural = 'Currencies'

    def __str__(self) -> str:
        return self.iso4217_code

    def save(self, *args, **kwargs):
        self.iso4217_code = self.iso4217_code.upper()
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse('plugins:netbox_ledger_tracker:currency', args=[self.pk])


class Ledger(NetBoxModel):
    """A named pool of shared expenses split between a group of people (e.g. a trip or a running house tab)."""

    clone_fields = ['currency', 'calc_method']

    name = models.CharField(max_length=100)
    currency = models.ForeignKey(to=Currency, on_delete=models.PROTECT, related_name='ledgers')
    closed = models.BooleanField(
        default=False,
        help_text='Closed ledgers no longer accept new people or expenses.',
    )
    calc_method = models.CharField(
        max_length=20,
        choices=LedgerCalcMethodChoices,
        default=_default_calc_method,
    )
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Ledger'
        verbose_name_plural = 'Ledgers'

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse('plugins:netbox_ledger_tracker:ledger', args=[self.pk])


class Person(NetBoxModel):
    """A participant in a Ledger. Optionally linked to a NetBox user account."""

    clone_fields = ['ledger']

    name = models.CharField(max_length=100)
    ledger = models.ForeignKey(to=Ledger, on_delete=models.CASCADE, related_name='people')
    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        related_name='ledger_people',
        blank=True,
        null=True,
        help_text='Optional: link this person to a NetBox user account.',
    )

    class Meta:
        ordering = ['ledger', 'name']
        unique_together = [['ledger', 'name']]
        verbose_name = 'Person'
        verbose_name_plural = 'People'

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse('plugins:netbox_ledger_tracker:person', args=[self.pk])


class Expense(NetBoxModel):
    """A single shared expense recorded against a Ledger."""

    clone_fields = ['ledger', 'currency', 'date']

    name = models.CharField(max_length=100)
    ledger = models.ForeignKey(to=Ledger, on_delete=models.CASCADE, related_name='expenses')
    currency = models.ForeignKey(to=Currency, on_delete=models.PROTECT, related_name='expenses')
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    amount_native = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        editable=False,
        help_text='Amount converted to the ledger currency at the time this expense was saved.',
    )
    date = models.DateField()
    people = models.ManyToManyField(to=Person, through='ExpensePart', related_name='expenses')
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', '-pk']
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse('plugins:netbox_ledger_tracker:expense', args=[self.pk])

    def clean(self):
        super().clean()
        if self.ledger_id and self.ledger.closed:
            raise ValidationError('Cannot add or edit expenses on a closed ledger.')


class ExpensePart(NetBoxModel):
    """One person's share of a single Expense: what they paid and what they owe."""

    expense = models.ForeignKey(to=Expense, on_delete=models.CASCADE, related_name='parts')
    person = models.ForeignKey(to=Person, on_delete=models.PROTECT, related_name='expense_parts')
    has_paid = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    has_paid_native = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    should_pay = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    should_pay_native = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    auto_amount = models.BooleanField(
        default=False,
        help_text="This person's share is auto-calculated as an even split of the expense remainder.",
    )

    class Meta:
        ordering = ['expense', 'person']
        unique_together = [['expense', 'person']]
        verbose_name = 'Expense Part'
        verbose_name_plural = 'Expense Parts'

    def __str__(self) -> str:
        return f'{self.person} / {self.expense}'

    def get_absolute_url(self) -> str:
        return reverse('plugins:netbox_ledger_tracker:expensepart', args=[self.pk])

    def clean(self):
        super().clean()
        if self.expense_id and self.person_id and self.expense.ledger_id != self.person.ledger_id:
            raise ValidationError('The expense and person must belong to the same ledger.')
