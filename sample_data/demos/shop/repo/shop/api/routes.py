"""A tiny router standing in for an HTTP API: a request dict in, (status, body) out."""
from shop.cart import Cart
from shop.catalog import PRODUCTS, UnknownProduct
from shop.checkout import checkout


def handle(request):
    method, path, body = request.get("method"), request.get("path"), request.get("body") or {}
    if (method, path) == ("GET", "/products"):
        return 200, {"products": PRODUCTS}
    if (method, path) == ("POST", "/checkout"):
        cart = Cart()
        try:
            for line in body.get("items", []):
                cart.add(line["sku"], line.get("qty", 1))
            return 200, checkout(cart)
        except UnknownProduct as e:
            return 400, {"error": f"unknown product {e.args[0]}"}
        except ValueError as e:
            return 400, {"error": str(e)}
    return 404, {"error": "not found"}
