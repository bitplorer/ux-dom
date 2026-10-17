"""Catalog with product cards."""
from __future__ import annotations

from app.components.layout import Shell
from app.document import page
from ux_dom import Component
from ux_dom.dom import a, div, h1, h2, p, span

__all__ = ["Shop"]

PRODUCTS = [
    {"id": "sku-a", "name": "Aurora Ring", "price": 120, "blurb": "Hand-finished gold."},
    {"id": "sku-b", "name": "Nimbus Watch", "price": 340, "blurb": "Titanium chronograph."},
    {"id": "sku-c", "name": "Solace Pendant", "price": 89, "blurb": "Minimal silver."},
]


class Shop(Component):
    def render(self):
        cards = [
            div(
                h2(prod["name"], className="font-semibold text-lg"),
                p(prod["blurb"], className="text-sm text-slate-600 mb-2"),
                span(f"${prod['price']}", className="badge"),
                " ",
                a(
                    "Add via cart →",
                    href="/cart",
                    className="text-sky-600 text-sm underline ml-2",
                ),
                id=prod["id"],
                className="card",
            )
            for prod in PRODUCTS
        ]
        return Shell(
            h1("Catalog", className="text-3xl font-bold mb-2"),
            p("Pure UxDom components · no SPA build step", className="text-slate-600 mb-6"),
            div(*cards, className="grid gap-3 sm:grid-cols-3", id="catalog"),
            active="shop",
        )


def get():
    return page(Shop(), page_title="Shop · Showcase")
