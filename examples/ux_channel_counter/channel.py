"""The channel side: state, one region, two actions.

* ``@ch.region`` renders a fragment the client can morph. Here it is a ux-dom
  component turned into a string.
* ``@ch.on(refresh=[...])`` registers an action; after it runs the listed
  regions are rendered again and sent back to the browser.
* ``ch.draft`` is ephemeral UI state. With the development memory store it is
  one value per process, shared by every visitor; ``change`` updates it
  atomically. Keep business data in your database.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from ux_channel import Channel, ChannelConfig

from .components import CounterCard

# Development config: memory stores, dev diagnostics. For production use
# ChannelConfig.production(secret).with_redis(url) and a real secret.
DEV_SECRET = "ux-dom-counter-demo-secret-32-chars!!"


def boot(app: FastAPI) -> Channel:
    config = ChannelConfig.development(
        secret=os.environ.get("UX_CHANNEL_SECRET", DEV_SECRET),
        allow_memory_stores=True,
    )
    return Channel.boot(app, config=config)


def register(ch: Channel):
    """Define the region and actions on ``ch``; return them for the page."""

    def current() -> int:
        return int(ch.draft.get("count", 0) or 0)

    @ch.region
    def counter(ctx):
        return CounterCard(count=current()).__render__(pretty=False)

    @ch.on(refresh=[counter], idempotent=False)
    def add(step: int = 1):
        ch.draft.change("count", lambda n: int(n or 0) + int(step), default=0)
        return ch.done()

    @ch.on(refresh=[counter], idempotent=False)
    def reset():
        ch.draft.set("count", 0)
        return ch.done(notice="Counter reset")

    return counter, add, reset
