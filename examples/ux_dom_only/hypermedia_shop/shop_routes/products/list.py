from ux_dom import Component, Document
from ux_dom.dom import a, div, h2, li, span, ul

__all__ = ['ProductList']

PRODUCTS = [
    {"id": "sku-a", "name": "Aurora Ring", "price": 120},
    {"id": "sku-b", "name": "Nimbus Watch", "price": 340},
    {"id": "sku-c", "name": "Solace Pendant", "price": 89},
]


class ProductList(Component):
    routes = ["get"]

    def render(self):
        items = [
            li(
                a(
                    f"{p['name']} — ${p['price']}",
                    href=f"/shop/products/{p['id']}/",
                    hx_boost="true",
                ),
                id=p["id"],
            )
            for p in PRODUCTS
        ]
        return div(
            h2("Catalog"),
            ul(*items, id="catalog"),
            span(a("← Home", href="/shop/index/Index")),
            id="product-list",
        )

    @classmethod
    def get(cls):
        return Document(ensure_csrf_token=False)(cls())
