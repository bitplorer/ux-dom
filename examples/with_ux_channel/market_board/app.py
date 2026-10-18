"""
Market board — **ux_dom + ux-channel** live topic fan-out (current API).

Run::

    uvicorn examples.with_ux_channel.market_board.app:app --host 0.0.0.0 --port 8094
"""
from __future__ import annotations

import asyncio
import os
import random

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from ux_channel import Channel, ChannelConfig, Region
from ux_channel.render.kit import attr_string, demo_scripts

SECRET = os.environ.get(
    "UX_CHANNEL_SECRET", "ux_dom-market-board-secret-32chars!!!!"
)

app = FastAPI(title="ux_dom+channel market board")
cfg = ChannelConfig.development(secret=SECRET, cek="off")
ch = Channel.boot(app, config=cfg)

STATE = {"price": 100.0, "ticks": 0}


class Ticker(Region):
    uid = "market.ticker"

    def render(self, ctx=None):
        return (
            f'<div class="card"><h2>Ticker</h2>'
            f'<p class="val">{STATE["price"]:.2f}</p>'
            f'<p class="muted">ticks {STATE["ticks"]}</p></div>'
        )

    @Region.action(broadcast="public.market")
    def bump(self):
        STATE["price"] = round(STATE["price"] * (1 + random.uniform(-0.01, 0.01)), 2)
        STATE["ticks"] += 1


ticker = Ticker(ch).mount()
ch.live.bind("public.market", ticker)


@app.on_event("startup")
async def _feeder():
    async def loop():
        while True:
            await asyncio.sleep(2.0)
            try:
                STATE["price"] = round(
                    STATE["price"] * (1 + random.uniform(-0.005, 0.005)), 2
                )
                STATE["ticks"] += 1
                ch.live.publish("public.market")
            except Exception:
                pass

    asyncio.create_task(loop())


@app.get("/health")
def health():
    return {"ok": True, "example": "market_board"}


@app.get("/")
def index():
    body = attr_string(ch.body_attrs(ws=True, push_topic="public.market"))
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"/><title>Market board</title>
{demo_scripts(ch)}
<style>
body{{font-family:system-ui;max-width:40rem;margin:2rem auto;padding:0 1rem}}
.card{{border:1px solid #e2e8f0;border-radius:12px;padding:1rem;margin:.75rem 0}}
.val{{font-size:2rem;font-weight:700}}
.muted{{color:#64748b}}
button{{background:#0f172a;color:#fff;border:0;border-radius:8px;padding:.6rem 1rem}}
</style></head>
<body {body}>
  <h1>Market board</h1>
  {ticker()}
  <p><button type="button" {ch.control(ticker.bump)}>Bump</button></p>
</body></html>"""
    return HTMLResponse(html)
