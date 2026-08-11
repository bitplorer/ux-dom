"""HtmxControl — HTMX script tags and optional middleware (optional SSE ext)."""
from __future__ import annotations

from typing import Any, Sequence

from ux_dom.dom import script


class HtmxControl:
    """HTMX control plane: scripts + partial policy + optional middleware.

    Does not own ``hx_*`` attribute compilation — that stays in Tags.clean_attribute.

    When ``sse=True``, also loads ``htmx-ext-sse`` so attributes like
    ``hx-ext="sse"``, ``sse-connect``, ``sse-swap`` work in the browser.
    Without that script, Live SSE demos sit forever on the placeholder text.
    """

    plugin_kind = "control"
    name = "htmx"

    def __init__(
        self,
        *,
        version: str = "1.9.2",
        idiomorph: bool = True,
        sse: bool = False,
        sse_version: str = "2.2.3",
        cdn: bool = True,
        middleware: bool = False,
    ):
        self.version = version
        self.idiomorph = idiomorph
        self.sse = sse
        self.sse_version = sse_version
        self.cdn = cdn
        self.middleware = middleware

    def artifacts(self):
        """CDN-only — no files to ship."""
        return ()

    def document_head(self) -> Sequence[Any]:
        return ()

    def document_body(self) -> Sequence[Any]:
        body: list[Any] = []
        if self.cdn:
            body.append(script(src=f"https://unpkg.com/htmx.org@{self.version}"))
            if self.idiomorph:
                body.append(
                    script(src="https://unpkg.com/idiomorph/dist/idiomorph-ext.min.js")
                )
            if self.sse:
                # Official HTMX 2 SSE extension (separate package from core).
                body.append(
                    script(src=f"https://unpkg.com/htmx-ext-sse@{self.sse_version}")
                )
        return body

    def wire(self, action: Any = None, **kwargs: Any) -> dict[str, Any]:
        """Pass-through for explicit hx kwargs (attrs already use Tags dialect)."""
        return dict(kwargs)

    def partial_policy(self, request: Any) -> str:
        headers = getattr(request, "headers", None) or {}
        get = headers.get if hasattr(headers, "get") else lambda k, d=None: d
        if get("hx-request") or get("HX-Request"):
            return "partial"
        return "full"

    def mount(self, app: Any, **kwargs: Any) -> None:
        if not self.middleware:
            return
        try:
            from ux_dom.htmx.middleware import HtmxMiddleware
        except Exception:
            return
        # Starlette/FastAPI style
        if hasattr(app, "add_middleware"):
            app.add_middleware(HtmxMiddleware)
