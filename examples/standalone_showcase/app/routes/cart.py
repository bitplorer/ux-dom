"""HTMX cart counter — get full page, post returns partial."""
from __future__ import annotations

import threading

from ux_dom import Component
from ux_dom.dom import button, div, h1, p, span

from app.components.layout import Shell
from app.document import page

__all__ = ["Cart"]

_CART = {"n": 0}
_CART_LOCK = threading.Lock()


class Cart(Component):
    routes = ["get", "post"]

    def render(self):
        with _CART_LOCK:
            n = _CART["n"]
        return div(
            h1("Cart", className="text-2xl font-bold mb-2"),
            p(
                "Click +1 — HTMX swaps only this card (POST partial).",
                className="text-slate-600 mb-4",
            ),
            div(
                span(f"{n} items", id="count", className="badge"),
                button(
                    "+1",
                    type="button",
                    hx_post="/cart/Cart",
                    hx_target="#cart-root",
                    hx_swap="outerHTML",
                    # Queue rapid clicks so concurrent presses don't drop updates
                    hx_sync="this:queue all",
                    className=(
                        "ml-3 rounded-lg bg-slate-900 text-white "
                        "px-4 py-2 text-sm font-medium"
                    ),
                    id="add-btn",
                ),
                className="flex items-center",
            ),
            id="cart-root",
            className="card max-w-md",
        )

    @classmethod
    def get(cls):
        return page(Shell(cls(), active="cart"), page_title="Cart · Showcase")

    @classmethod
    def post(cls):
        with _CART_LOCK:
            _CART["n"] += 1
        return cls()
