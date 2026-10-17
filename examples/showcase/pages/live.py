"""Live updates: server-sent events and a streamed page.

``/sse`` connects with the htmx SSE extension (loaded by ``Htmx(sse=True)``)
to ``/api/sse``; each event carries an HTML fragment that htmx swaps in.
``/stream`` is served by ``StreamingRoute``: the tree is sent in chunks while
it renders, which suits long pages.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import Request
from fastapi.responses import StreamingResponse

from ux_dom.dom import div, h1, li, ol, p, span

from ..components import Shell
from ..document import page


def sse_page():
    return page(
        Shell(
            h1("Live"),
            p("A tick arrives every second over server-sent events."),
            div(
                "waiting for the first tick…",
                hx_ext="sse",
                sse_connect="/api/sse",
                sse_swap="message",
                id="tick",
                className="card mono",
            ),
            active="/sse",
        ),
        page_title="Live · UxDom Showcase",
    )


def sse_event(html: str, event: str = "message") -> str:
    """One SSE frame; multi-line HTML becomes one ``data:`` line per line."""
    data = "".join(f"data: {line}\n" for line in html.splitlines())
    return f"event: {event}\n{data}\n"


async def sse_feed(request: Request, n: int = 0):
    """``event: message`` frames whose data is a rendered fragment.

    ``n`` limits the number of ticks (tests use it); ``0`` streams forever.
    """

    async def frames() -> AsyncIterator[str]:
        i = 0
        while n == 0 or i < n:
            if await request.is_disconnected():
                break
            yield sse_event(str(span(f"tick #{i}", className="tick")))
            i += 1
            await asyncio.sleep(0.01 if n else 1.0)

    return StreamingResponse(
        frames(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def stream_page():
    rows = [li(f"Row {i}", id=f"row-{i}") for i in range(50)]
    return page(
        Shell(
            h1("Stream"),
            p("This page is streamed in chunks by StreamingRoute."),
            ol(*rows, className="card"),
            active="/stream",
        ),
        page_title="Stream · UxDom Showcase",
    )
