"""The product catalog. Prices are integer cents so totals never drift."""

PRODUCTS = {
    "mug": {"name": "Enamel mug", "price": 1299},
    "tee": {"name": "Cotton tee", "price": 2400},
    "cap": {"name": "Canvas cap", "price": 1850},
    "pin": {"name": "Enamel pin", "price": 499},
}


class UnknownProduct(KeyError):
    pass


def price_of(sku):
    try:
        return PRODUCTS[sku]["price"]
    except KeyError:
        raise UnknownProduct(sku) from None
