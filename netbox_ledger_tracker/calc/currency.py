from decimal import Decimal, localcontext


def convert_currency(amount, from_currency, to_currency):
    """Convert ``amount`` between two Currency instances via their shared base_rate."""
    if from_currency.pk == to_currency.pk:
        return Decimal(amount)
    base_amount = Decimal(amount) * from_currency.base_rate
    return base_amount / to_currency.base_rate


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
