"""
Market board — **ux_dom + ux-channel** live topic fan-out.

Demonstrates:
* ``@Region.action`` + ``ch.live.bind/publish``
* UxDom layout shell + region HTML slots
* Background feeder (simulates market ticks) via lifespan

Run::

    uvicorn examples.with_ux_channel.market_board.app:app --host 0.0.0.0 --port 8094
"""
from __future__ import annotations

import asyncio
import os
import random
from contextlib import asynccontextmanager

from fastapi import FastAPI
from ux_dom import Component
from ux_dom.dom import button, div, h1, h2, p, raw, span

from ux_channel import Channel, ChannelConfig, Region
from ux_channel.response import HTMLResponse

SECRET = os.environ.get(
    "UID_CHANNEL_SECRET", "ux_dom-market-board-secret-32chars!!!!"
)

STATE = {"price": 100.0, "ticks": 0}


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def loop():
        while True:
            await asyncio.sleep(2.0)
            try:
                STATE["price"] = round(
                    STATE["price"] + random.choice([-0.5, 0, 0.3, 0.8]), 2
                )
                STATE["ticks"] += 1
                ch.live.publish("public.market")
            except Exception:
                pass

    task = asyncio.create_task(loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="ux_dom+channel market board", lifespan=lifespan)
if os.environ.get("REDIS_URL"):
    cfg = ChannelConfig.production(SECRET).with_redis(os.environ["REDIS_URL"])
else:
    cfg = ChannelConfig.development(secret=SECRET, allow_memory_stores=True)
ch = Channel.boot(app, config=cfg)


class Ticker(Region):
    uid = "market.ticker"

    def render(self, ctx=None):
        return div(
            h2("Ticker"),
            span(f"{STATE['price']:.2f}", className="price", id="px"),
            span(f" ticks={STATE['ticks']}", className="muted"),
            data_channel_id=self.uid,
            className="card",
        ).__render__(pretty=False)

    @Region.action(broadcast="public.market")
    def bump(self):
        STATE["price"] = round(STATE["price"] + random.uniform(-1.5, 2.0), 2)
        STATE["ticks"] += 1


class Status(Region):
    uid = "market.status"

    def render(self, ctx=None):
        trend = "up" if STATE["price"] >= 100 else "down"
        return div(
            f"Status · {trend} · last={STATE['price']:.2f}",
            data_channel_id=self.uid,
            className="card muted",
        ).__render__(pretty=False)


ticker = Ticker(ch).mount()
status = Status(ch).mount()
ch.live.bind("public.market", ticker, status)

_STYLE = """
<style>
  :root { font-family: system-ui, sans-serif; color: #0f172a; background: #0b1220; }
  body { max-width: 36rem; margin: 2rem auto; padding: 0 1rem; color: #e2e8f0; }
  .card { background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 1rem 1.25rem; margin: .75rem 0; }
  .price { font-size: 2rem; font-weight: 700; color: #38bdf8; }
  .muted { color: #94a3b8; }
  button { background: #38bdf8; color: #0b1220; border: 0; border-radius: 8px; padding: .55rem 1rem; font-weight: 600; cursor: pointer; }
</style>
"""


class BoardPage(Component):
    def render(self):
        return div(
            h1("Market Board"),
            p("UxDom shell · channel regions + live topic public.market"),
            raw(ticker()),
            raw(status()),
            p(
                button(
                    "Manual bump",
                    type="button",
                    **ch.control(ticker.bump).as_ux_dom(),
                )
            ),
            id="board",
        )


@app.get("/health")
def health():
    return {"ok": True, "app": "with_ux_channel.market_board", "state": dict(STATE)}


@app.get("/")
def index():
    scripts = ch.scripts() if hasattr(ch, "scripts") else ""
    body_attrs = ""
    if hasattr(ch, "body_attr_string"):
        try:
            body_attrs = ch.body_attr_string(ws=True, push_topic="public.market")
        except TypeError:
            try:
                body_attrs = ch.body_attr_string(ws=True)
            except TypeError:
                body_attrs = ""
    inner = BoardPage().__render__(pretty=False)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Market Board · ux_dom + ux-channel</title>
  {_STYLE}
  {scripts}
</head>
<body {body_attrs}>
{inner}
</body>
</html>"""
    return HTMLResponse(html)
