"""
Live cart — **ux_dom + ux-channel** (current Channel/Region API).

Run::

    uvicorn examples.with_ux_channel.live_cart.app:app --host 0.0.0.0 --port 8093
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from ux_channel import Channel, ChannelConfig, Region
from ux_channel.render.kit import attr_string, demo_scripts

SECRET = os.environ.get(
    "UX_CHANNEL_SECRET", "ux_dom-live-cart-secret-key-32chars!!"
)

app = FastAPI(title="ux_dom+channel live cart")
if os.environ.get("REDIS_URL"):
    cfg = ChannelConfig.production(SECRET, cek="off").with_redis(os.environ["REDIS_URL"])
else:
    cfg = ChannelConfig.development(secret=SECRET, cek="off")
ch = Channel.boot(app, config=cfg)

DB: dict[str, Any] = {
    "stock": {"sku-a": 100, "sku-b": 50},
    "names": {"sku-a": "Aurora Ring", "sku-b": "Nimbus Watch"},
    "cart": {},
}


class CartBadge(Region):
    uid = "live.cart"

    def render(self, ctx=None):
        n = sum(int(v) for v in DB["cart"].values())
        return (
            f'<div class="card"><h2>Cart</h2>'
            f'<p><span class="val">{n}</span> items</p></div>'
        )

    @Region.action
    def add(self, sku: str = "sku-a"):
        DB["cart"][sku] = int(DB["cart"].get(sku, 0)) + 1
        DB["stock"][sku] = max(0, int(DB["stock"].get(sku, 0)) - 1)


cart = CartBadge(ch).mount()


@app.get("/health")
def health():
    return {"ok": True, "example": "live_cart"}


@app.get("/")
def index():
    body = attr_string(ch.body_attrs(ws=True))
    add_btn = f'<button type="button" {ch.control(cart.add)}>Add Aurora</button>'
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"/><title>Live Cart</title>
{demo_scripts(ch)}
<style>
body{{font-family:system-ui;max-width:40rem;margin:2rem auto;padding:0 1rem}}
.card{{border:1px solid #e2e8f0;border-radius:12px;padding:1rem;margin:.75rem 0}}
.val{{font-size:1.5rem;font-weight:700}}
</style></head>
<body {body}>
  <h1>Live Cart</h1>
  <p>ux-channel Region actions · catalog below</p>
  {cart()}
  <div class="card"><h2>Catalog</h2><p>Aurora Ring</p>{add_btn}</div>
</body></html>"""
    return HTMLResponse(html)
