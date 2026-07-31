from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel

from .calc.currency import rate_between
from .choices import LedgerCalcMethodChoices, SettlementMethodChoices

User = get_user_model()

# Money is stored to two places; conversions round half-up rather than the
# decimal module's default banker's rounding, which is what people expect on a bill.
MONEY_QUANT = Decimal('0.01')


def _to_money(value):
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


class FrozenRateMixin:
    """Restates ``amount`` in the ledger currency using a rate frozen on first save.

    Deliberately a plain mixin rather than an abstract model: the concrete models
    declare their own columns, so this contributes no fields and cannot perturb
    their migrations. Consumers must provide ``ledger``, ``currency``, ``amount``,
    ``amount_native`` and ``fx_rate``.

    Deriving here rather than in a view means every write path -- a bespoke
    screen, the plain edit form, bulk import, clone, the REST API and any script
    -- converts identically and none can forget to. Freezing the rate means a
    later run of ``get_ledger_currency_rates`` cannot silently re-price figures
    people have already settled on.
    """

    @classmethod
    def from_db(cls, db, field_names, values):
        # Remember which currency/ledger this row was loaded with so save() can tell
        # whether the frozen fx_rate still applies.
        instance = super().from_db(db, field_names, values)
        instance._loaded_currency_id = getattr(instance, 'currency_id', None)
        instance._loaded_ledger_id = getattr(instance, 'ledger_id', None)
        return instance

    def _derive_native_amounts(self):
        if not (self.ledger_id and self.currency_id):
            return

        rate_is_stale = (
            self.fx_rate is None
            or self._state.adding
            or self.currency_id != getattr(self, '_loaded_currency_id', self.currency_id)
            or self.ledger_id != getattr(self, '_loaded_ledger_id', self.ledger_id)
        )
        if rate_is_stale:
            self.fx_rate = rate_between(self.currency, self.ledger.currency)

        self.amount_native = _to_money(self.amount * self.fx_rate)

    def full_clean(self, *args, **kwargs):
        # clean_fields() runs before clean() and would reject the not-null
        # amount_native/fx_rate before any hook could populate them.
        self._derive_native_amounts()
        super().full_clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self._derive_native_amounts()
        super().save(*args, **kwargs)
        self._loaded_currency_id = self.currency_id
        self._loaded_ledger_id = self.ledger_id


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


class Expense(FrozenRateMixin, NetBoxModel):
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
    fx_rate = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        editable=False,
        help_text=(
            'Ledger-currency units per unit of the expense currency. Frozen when the '
            'expense is first saved, so later exchange-rate updates do not silently '
            're-price historical expenses.'
        ),
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

    def _derive_native_amounts(self):
        """Restate this person's paid/owed amounts using the parent expense's frozen rate.

        Always derived, never trusted from the caller, so a part cannot drift out
        of step with the expense it belongs to.
        """
        if not self.expense_id:
            return
        rate = self.expense.fx_rate
        if rate is None:
            return
        self.has_paid_native = _to_money(self.has_paid * rate)
        self.should_pay_native = _to_money(self.should_pay * rate)

    def full_clean(self, *args, **kwargs):
        self._derive_native_amounts()
        super().full_clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self._derive_native_amounts()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.expense_id and self.person_id and self.expense.ledger_id != self.person.ledger_id:
            raise ValidationError('The expense and person must belong to the same ledger.')


class Settlement(FrozenRateMixin, NetBoxModel):
    """A real payment made between two people to pay down what the ledger says they owe.

    Expenses record what was *spent*; settlements record what has since been
    *paid back*. Without them the Settle Up matrix would keep reporting a debt
    that has already been cleared, and the only workaround would be inventing a
    fake compensating expense.
    """

    clone_fields = ['ledger', 'currency', 'date', 'method']

    ledger = models.ForeignKey(to=Ledger, on_delete=models.CASCADE, related_name='settlements')
    from_person = models.ForeignKey(
        to=Person,
        on_delete=models.PROTECT,
        related_name='settlements_paid',
        verbose_name='From',
        help_text='The person who handed over the money.',
    )
    to_person = models.ForeignKey(
        to=Person,
        on_delete=models.PROTECT,
        related_name='settlements_received',
        verbose_name='To',
        help_text='The person who received it.',
    )
    currency = models.ForeignKey(to=Currency, on_delete=models.PROTECT, related_name='settlements')
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    amount_native = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        editable=False,
        help_text='Amount converted to the ledger currency at the time this settlement was saved.',
    )
    fx_rate = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        editable=False,
        help_text=(
            'Ledger-currency units per unit of the settlement currency. Frozen when the '
            'settlement is first saved, so later exchange-rate updates do not silently '
            're-price it.'
        ),
    )
    date = models.DateField()
    method = models.CharField(max_length=30, choices=SettlementMethodChoices, blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', '-pk']
        verbose_name = 'Settlement'
        verbose_name_plural = 'Settlements'

    def __str__(self) -> str:
        return f'{self.from_person} to {self.to_person}: {self.amount} {self.currency}'

    def get_absolute_url(self) -> str:
        return reverse('plugins:netbox_ledger_tracker:settlement', args=[self.pk])

    def get_method_color(self):
        return SettlementMethodChoices.colors.get(self.method)

    def clean(self):
        super().clean()
        if self.from_person_id and self.from_person_id == self.to_person_id:
            raise ValidationError('A settlement must be between two different people.')
        if self.ledger_id:
            if self.ledger.closed:
                raise ValidationError('Cannot add or edit settlements on a closed ledger.')
            for field, person in (('from_person', self.from_person), ('to_person', self.to_person)):
                if person is not None and person.ledger_id != self.ledger_id:
                    raise ValidationError({field: 'This person belongs to a different ledger.'})
