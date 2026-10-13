# tinyshop

A small, dependency-free shop backend used as the demo repo for Lucidity: a product catalog,
a cart, pricing (tax), checkout, and a tiny request router standing in for an HTTP API.

```
python -m pytest -q tests     # what works today
python -m pytest -q spec      # acceptance tests for features nobody has built yet
```

## Layout

- `shop/catalog`: products and prices, in cents
- `shop/cart`: a cart of SKUs and quantities
- `shop/pricing`: tax
- `shop/checkout`: turns a cart into a receipt
- `shop/api`: routes requests like `POST /checkout` to the code above
