"""htmx partial: the form POSTs, the server returns only the cart card.

Without JavaScript the same form does a normal POST and the server redirects
back (post/redirect/get). ``hx-post`` uses a relative URL: ux-dom only lets
htmx request same-origin URLs; another origin needs ``cross_origin(url)``.
"""

from __future__ import annotations

import threading

from fastapi import Request
from fastapi.responses import RedirectResponse

from ux_dom import Component
from ux_dom.dom import button, form, h1, p, span

from ..components import Shell
from ..document import page

_lock = threading.Lock()
_items = 0  # process-local demo state; use a database in a real app


class CartCard(Component):
    def render(self, count: int):
        return form(
            span(f"{count} items", className="badge"),
            button("Add one", type="submit"),
            method="post",
            action="/cart",
            hx_post="/cart",
            hx_swap="outerHTML",
            hx_sync="this:queue all",
            id="cart",
            data_count=str(count),
            className="card",
        )


def get():
    return page(
        Shell(
            h1("Cart"),
            p("The button swaps only this card; the page never reloads."),
            CartCard(count=_items),
            active="/cart",
        ),
        page_title="Cart · UxDom Showcase",
    )


def post(request: Request):
    global _items
    with _lock:
        _items += 1
        count = _items
    if request.state.htmx:
        return CartCard(count=count)
    return RedirectResponse("/cart", status_code=303)
