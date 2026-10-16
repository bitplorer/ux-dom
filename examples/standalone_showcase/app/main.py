"""
Standalone UxDom showcase — ASGI entry.

    uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

From repo root::

    PYTHONPATH=examples/standalone_showcase uvicorn app.main:app --port 8080
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse as ASGIStreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import WebSocketRoute
from starlette.types import ASGIApp

from ux_dom.dom import div, h2, p
from ux_dom.plugins import App
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.routing import DirectoryRouting
from ux_dom.response.starlette import StreamingResponse

from app import settings

PACKAGE = Path(__file__).resolve().parent


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline browser hardening headers (safe defaults, no capability loss)."""

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        # CSP: allow HTMX CDN + self; unsafe-inline not required for this demo's scripts (src=)
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'self'; "
            "base-uri 'self'",
        )
        return response


_builder = (
    App(debug=settings.DEBUG)
    .use(
        DirectoryRouting(
            package_dir=PACKAGE,
            base_directory="routes",
            prefix="",
        )
    )
    # sse=True loads htmx-ext-sse so Live SSE page (sse-connect) actually works
    .use(HtmxControl(middleware=True, version="2.0.4", sse=True))
)

def _hot_reload():
    """Dev-only HMR route, or None. Its watcher runs via the app lifespan."""
    if not (settings.WITH_HMR and settings.DEBUG):
        return None
    from fastapi import WebSocket

    from ux_dom.reloader import HotReloadWebSocketRoute, WatchPath

    return HotReloadWebSocketRoute(
        websocket_type=WebSocket,
        watch_paths=[
            WatchPath(path=str(PACKAGE), on_reload=()),
            WatchPath(path=str(settings.BASE_DIR / "assets"), on_reload=()),
        ],
        url_path="/hot-reload",
        url_name="hot-reload",
    )


_hot = _hot_reload()


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if _hot is not None:
        await _hot.startup()
    try:
        yield
    finally:
        if _hot is not None:
            await _hot.shutdown()


app = _builder.build(
    asgi=FastAPI(title=settings.APP_TITLE, debug=settings.DEBUG, lifespan=_lifespan)
)

if _hot is not None:
    # HotReloadWebSocketRoute is a raw ASGI app; Starlette mounts it as-is.
    app.router.routes.append(WebSocketRoute(_hot.url_path, _hot, name=_hot.url_name))
app.add_middleware(SecurityHeadersMiddleware)

try:
    from fastapi.staticfiles import StaticFiles

    css_dir = settings.webassets.static.css
    js_dir = settings.webassets.static.js
    if Path(str(css_dir)).exists():
        app.mount("/css", StaticFiles(directory=str(css_dir), check_dir=False), name="css")
    if Path(str(js_dir)).exists():
        app.mount("/js", StaticFiles(directory=str(js_dir), check_dir=False), name="js")
    if settings.ASSETS_DIR.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(settings.ASSETS_DIR)),
            name="assets",
        )
except Exception:
    pass



@app.get("/health", response_class=JSONResponse)
def health():
    return {
        "ok": True,
        "app": "ux_dom-standalone-showcase",
        "title": settings.APP_TITLE,
        "debug": settings.DEBUG,
        "features": ["components", "directory_router", "htmx", "sse", "stream", "tailwind"],
    }


@app.get("/api/sse")
async def api_sse(request: Request, n: int = 0):
    """SSE ticker for HTMX sse-ext.

    Emits ``event: message`` with HTML ``data`` so ``sse-swap="message"`` can
    replace the tick card content. Pass ``?n=5`` for a finite stream (tests).
    """

    async def gen() -> AsyncIterator[str]:
        # Comment frame forces clients/proxies to flush headers immediately
        yield ": connected\n\n"
        i = 0
        while n == 0 or i < n:
            if await request.is_disconnected():
                break
            html = f'<span class="tick">tick #{i}</span>'
            yield f"event: message\ndata: {html}\n\n"
            i += 1
            await asyncio.sleep(0.05 if n else 1.0)

    return ASGIStreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/stream")
def api_stream():
    """Compact HTML stream via ux_dom StreamingResponse."""
    return StreamingResponse(
        div(
            h2("Streamed fragment"),
            p("Produced by ux_dom.response.StreamingResponse"),
            id="streamed",
        )
    )


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    run()
