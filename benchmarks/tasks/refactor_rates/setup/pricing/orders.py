from .rates import tax_rate


def total_cents(price_cents, qty, country):
    return round(price_cents * qty * (1 + tax_rate(country)))


def apply_discount(total_cents, code):
    raise NotImplementedError("discount codes are not implemented")
