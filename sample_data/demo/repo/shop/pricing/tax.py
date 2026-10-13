"""Sales tax, rounded half up to the cent."""

TAX_RATE = 0.08


def tax_on(cents, rate=TAX_RATE):
    return int(cents * rate + 0.5)
