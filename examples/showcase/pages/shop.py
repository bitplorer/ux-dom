"""Catalog whose descriptions come from a CMS as HTML.

HTML you did not write goes through ``defHTML``: formatting such as
``<strong>`` survives; scripts, event handlers, Alpine and htmx attributes
are dropped together with their content.
"""

from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import article, defHTML, div, h1, h2, p, span

from ..components import Shell
from ..document import page

# Pretend this came from a CMS: editors can format text, attackers can try more.
PRODUCTS = (
    {
        "sku": "ring",
        "name": "Aurora Ring",
        "price": 120,
        "html": "Hand-finished <strong>18k gold</strong>.",
    },
    {
        "sku": "watch",
        "name": "Nimbus Watch",
        "price": 340,
        "html": 'Titanium <em>chronograph</em>.<img src=x onerror="alert(1)">',
    },
    {
        "sku": "pendant",
        "name": "Solace Pendant",
        "price": 89,
        "html": 'Minimal silver.<script>steal()</script><b x-init="steal()">!</b>',
    },
)


class ProductCard(Component):
    def render(self, product: dict):
        return article(
            h2(product["name"]),
            p(*defHTML(product["html"])),
            span(f"${product['price']}", className="price"),
            id=f"product-{product['sku']}",
            className="card",
        )


def get():
    return page(
        Shell(
            h1("Shop"),
            p("Descriptions are CMS HTML, sanitized with defHTML."),
            div(*[ProductCard(product=x) for x in PRODUCTS], className="grid"),
            active="/shop",
        ),
        page_title="Shop · UxDom Showcase",
    )
