from decimal import Decimal, localcontext

# Precision of a stored exchange rate, matching Expense.fx_rate's decimal_places.
FX_RATE_QUANT = Decimal('0.0000000001')


def rate_between(from_currency, to_currency):
    """Return how many ``to_currency`` units one ``from_currency`` unit buys.

    Quantized to ``FX_RATE_QUANT`` so the value a caller stores is exactly the
    one it converts with -- otherwise a rate rounded on its way into the
    database would no longer reproduce the converted amount saved alongside it.
    """
    if from_currency.pk == to_currency.pk:
        return Decimal(1).quantize(FX_RATE_QUANT)
    return (Decimal(from_currency.base_rate) / Decimal(to_currency.base_rate)).quantize(FX_RATE_QUANT)


def convert_currency(amount, from_currency, to_currency):
    """Convert ``amount`` between two Currency instances via their shared base_rate."""
    return Decimal(amount) * rate_between(from_currency, to_currency)


def fraction_to_decimal(value, precision=2):
    """Convert a ``Fraction`` (or int) to a ``Decimal`` rounded to ``precision`` places."""
    if value == 0:
        return Decimal('0')
    whole = int(value)
    text = f'{whole}.'
    remainder = value - whole
    with localcontext() as ctx:
        ctx.prec = precision + len(str(abs(whole))) + 2
        text += str(Decimal(remainder.numerator) / remainder.denominator).partition('.')[2]
    return Decimal(text).quantize(Decimal('1.' + '0' * precision))


def result_to_decimal(result, precision=2):
    """Convert every ``Fraction`` amount in a ``{payer: {receiver: Fraction}}`` dict to ``Decimal``."""
    return {
        payer_id: {receiver_id: fraction_to_decimal(amount, precision) for receiver_id, amount in receivers.items()}
        for payer_id, receivers in result.items()
    }
