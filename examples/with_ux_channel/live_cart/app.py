"""
Live cart — **ux_dom + ux-channel** (production shape).

UxDom owns documents & markup. ux-channel owns trust, actions, region morph,
and client scripts.

Run::

    uvicorn examples.with_ux_channel.live_cart.app:app --host 0.0.0.0 --port 8093
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from ux_dom import Component
from ux_dom.dom import button, div, h1, h2, p, raw, span

from ux_channel import Channel, ChannelConfig, Region
from ux_channel.demo import attr_string, demo_scripts
from ux_channel.response import HTMLResponse

SECRET = os.environ.get(
    "UX_CHANNEL_SECRET", "ux_dom-live-cart-secret-key-32chars!!"
)

app = FastAPI(title="ux_dom+channel live cart")
if os.environ.get("REDIS_URL"):
    cfg = ChannelConfig.production(SECRET).with_redis(os.environ["REDIS_URL"])
else:
    cfg = ChannelConfig.development(secret=SECRET, allow_memory_stores=True)
ch = Channel.boot(app, config=cfg)

DB: dict[str, Any] = {
    "stock": {"sku-a": 100, "sku-b": 50, "sku-c": 25},
    "names": {
        "sku-a": "Aurora Ring",
        "sku-b": "Nimbus Watch",
        "sku-c": "Solace Pendant",
    },
    "cart": {},
}


def cart_count() -> int:
    return int(sum(DB["cart"].values()))


class CartBadge(Region):
    uid = "cart.badge"

    def render(self, ctx=None):
        return span(
            f"Cart ({cart_count()})",
            className="badge",
            data_channel_id=self.uid,
        ).__render__(pretty=False)


class CartPanel(Region):
    uid = "cart.panel"

    def render(self, ctx=None):
        if not DB["cart"]:
            return div(
                p("Your cart is empty."),
                data_channel_id=self.uid,
                className="panel empty",
            ).__render__(pretty=False)
        lines = [
            div(
                span(f"{DB['names'].get(sku, sku)} × {qty}"),
                className="line",
            )
            for sku, qty in DB["cart"].items()
        ]
        return div(*lines, data_channel_id=self.uid, className="panel").__render__(
            pretty=False
        )


class StockBoard(Region):
    uid = "stock.board"

    def render(self, ctx=None):
        rows = []
        for sku, qty in DB["stock"].items():
            rows.append(
                div(
                    span(f"{DB['names'][sku]} — stock {qty} "),
                    button(
                        "Add",
                        type="button",
                        **ch.control(add_to_cart, trust_sku=sku).as_ux_dom(),
                    ),
                    className="row",
                    id=sku,
                )
            )
        return div(*rows, data_channel_id=self.uid, className="stock").__render__(
            pretty=False
        )


badge = CartBadge(ch).mount()
panel = CartPanel(ch).mount()
stock = StockBoard(ch).mount()


@ch.on(refresh=[badge, panel, stock], idempotent=False)
def add_to_cart(sku: str = "sku-a"):
    if sku not in DB["stock"] or DB["stock"][sku] <= 0:
        return
    DB["stock"][sku] -= 1
    DB["cart"][sku] = DB["cart"].get(sku, 0) + 1


@ch.on(refresh=[badge, panel, stock], idempotent=False)
def clear_cart():
    for sku, qty in list(DB["cart"].items()):
        DB["stock"][sku] = DB["stock"].get(sku, 0) + qty
    DB["cart"].clear()


_STYLE = """
<style>
  :root { font-family: system-ui, sans-serif; color: #0f172a; background: #f8fafc; }
  body { max-width: 42rem; margin: 2rem auto; padding: 0 1rem; }
  .badge { background: #0f172a; color: #fff; padding: .25rem .6rem; border-radius: 999px; }
  .panel, .stock { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem; margin: .75rem 0; }
  .row, .line { display: flex; align-items: center; justify-content: space-between; gap: .5rem; padding: .35rem 0; }
  button { background: #0f172a; color: #fff; border: 0; border-radius: 8px; padding: .45rem .9rem; cursor: pointer; }
  button.danger { background: #b91c1c; }
  .header { display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem; }
</style>
"""


class ShopPage(Component):
    def render(self):
        return div(
            h1("Live Cart"),
            p("UxDom markup · ux-channel actions, caps, region morph."),
            div(
                raw(badge()),
                button(
                    "Clear cart",
                    type="button",
                    className="danger",
                    **ch.control(clear_cart).as_ux_dom(),
                ),
                className="header",
            ),
            h2("Catalog"),
            raw(stock()),
            h2("Cart"),
            raw(panel()),
            id="shop",
        )


@app.get("/health")
def health():
    return {
        "ok": True,
        "app": "with_ux_channel.live_cart",
        "cart": dict(DB["cart"]),
        "stock": dict(DB["stock"]),
    }


@app.get("/")
def index():
    """ux-dom markup + ux-channel client (scripts + body endpoint attrs)."""
    page = ShopPage()
    body_open = attr_string(ch.body_attrs())
    scripts = demo_scripts(ch, bridge=True, inspector=True)
    inner = page.__render__(pretty=False)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Live Cart · ux-dom + ux-channel</title>
  {_STYLE}
  {scripts}
</head>
<body {body_open}>
{inner}
</body>
</html>"""
    return HTMLResponse(html)
