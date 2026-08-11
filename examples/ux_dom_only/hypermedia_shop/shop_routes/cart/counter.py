"""Cart counter — classmethod routes get/post coexist with DOM get."""
from ux_dom import Component, Document
from ux_dom.dom import button, div, h2, span

__all__ = ["CartCounter"]

# process-local demo store (single worker)
_CART = {"n": 0}


class CartCounter(Component):
    routes = ["get", "post"]

    def render(self, n: int | None = None):
        count = _CART["n"] if n is None else n
        return div(
            h2("Cart"),
            span(f"{count} items", id="count", className="badge"),
            button(
                "+1",
                type="button",
                hx_post="/shop/cart/counter/CartCounter",
                hx_target="#cart-root",
                hx_swap="outerHTML",
                id="add-btn",
            ),
            id="cart-root",
        )

    @classmethod
    def get(cls):
        return Document(ensure_csrf_token=False)(cls())

    @classmethod
    def post(cls):
        _CART["n"] += 1
        # HTMX partial: fragment only (no full document)
        return cls()
