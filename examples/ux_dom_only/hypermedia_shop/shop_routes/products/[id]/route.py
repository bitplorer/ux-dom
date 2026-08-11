"""Dynamic product page: products/[id] → /shop/products/{id}/"""
from ux_dom.dom import a, div, h2, p, span

__all__ = ["get"]

PRODUCTS = {
    "sku-a": {"name": "Aurora Ring", "price": 120, "desc": "Hand-finished gold ring."},
    "sku-b": {"name": "Nimbus Watch", "price": 340, "desc": "Titanium chronograph."},
    "sku-c": {"name": "Solace Pendant", "price": 89, "desc": "Minimal silver pendant."},
}


def get(id: str):
    prod = PRODUCTS.get(id)
    if not prod:
        return div(h2("Not found"), p(f"No product {id}"), id="missing")
    return div(
        h2(prod["name"]),
        p(prod["desc"]),
        span(f"${prod['price']}", className="price"),
        p(a("← Catalog", href="/shop/products/list/ProductList")),
        id="product",
        data_product_id=id,
    )
