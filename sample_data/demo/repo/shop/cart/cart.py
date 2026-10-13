"""A cart: SKUs and quantities, priced from the catalog."""
from shop.catalog import price_of


class Cart:
    def __init__(self):
        self.items = {}

    def add(self, sku, qty=1):
        if qty <= 0:
            raise ValueError("quantity must be positive")
        price_of(sku)  # unknown products fail here, not at checkout
        self.items[sku] = self.items.get(sku, 0) + qty
        return self

    def remove(self, sku):
        self.items.pop(sku, None)
        return self

    def subtotal(self):
        return sum(price_of(sku) * qty for sku, qty in self.items.items())
