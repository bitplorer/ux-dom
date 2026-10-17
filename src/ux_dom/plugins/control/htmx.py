"""HtmxControl — HTMX script tags and optional middleware (optional SSE ext)."""
from __future__ import annotations

from typing import Any, Sequence

from ux_dom.dom import script

_UNPKG = "https://unpkg.com"
# Exact CDN files with Subresource Integrity (sha384). Each hash was computed
# on 2026-10-17 from unpkg and matched byte-for-byte on jsDelivr. A version
# not listed here is refused: without its hash the browser could run any
# bytes the CDN serves. Host other versions yourself with ``cdn=False``.
PINNED_SCRIPTS: dict[str, dict[str, tuple[str, str]]] = {
    "1.9.12": {
        "htmx": (
            f"{_UNPKG}/htmx.org@1.9.12/dist/htmx.min.js",
            "sha384-ujb1lZYygJmzgSwoxRggbCHcjc0rB2XoQrxeTUQyRjrOnlCoYta87iKBWq3EsdM2",
        ),
        # htmx 1.x ships its SSE extension inside htmx.org.
        "sse": (
            f"{_UNPKG}/htmx.org@1.9.12/dist/ext/sse.js",
            "sha384-OZrRw8/Zvv0VFGJJF6TN3gABVZvvO60Xz7RWkQKAmoRe+t1dc5J/ySJvXbpL+N+Q",
        ),
    },
    "2.0.4": {
        "htmx": (
            f"{_UNPKG}/htmx.org@2.0.4/dist/htmx.min.js",
            "sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+",
        ),
        # htmx 2.x moved extensions to separate packages.
        "sse": (
            f"{_UNPKG}/htmx-ext-sse@2.2.3/dist/sse.min.js",
            "sha384-Y4gc0CK6Kg+hmulDc6rZPJu0tqvk7EWlih0Oh+2OkAi1ZDlCbBDCQEE2uVk472Ky",
        ),
    },
}
IDIOMORPH_SCRIPT = (
    f"{_UNPKG}/idiomorph@0.8.0/dist/idiomorph-ext.min.js",
    "sha384-+iBk70O0UWQdSjXQSQ7amSxXCrsWq/6UOtvC9rDo0p7telbTSOyttExq6QCFBzNk",
)
DEFAULT_VERSION = "1.9.12"
# Every CDN URL this control can emit (CSP allows exactly these files).
CDN_SCRIPT_URLS: tuple[str, ...] = tuple(
    url for files in PINNED_SCRIPTS.values() for url, _ in files.values()
) + (IDIOMORPH_SCRIPT[0],)


def _pinned_script(url_and_hash: tuple[str, str]):
    url, integrity = url_and_hash
    return script(src=url, integrity=integrity, crossorigin="anonymous")


class HtmxControl:
    """HTMX control plane: scripts + partial policy + optional middleware.

    Does not own ``hx_*`` attribute compilation — that stays in Tags.clean_attribute.

    Scripts are exact CDN files with ``integrity`` and ``crossorigin``
    (see ``PINNED_SCRIPTS``). ``version`` picks a pinned htmx line
    (``1.9.12`` default, ``2.0.4``). ``sse=True`` adds the SSE extension that
    matches that line. ``cdn=False`` emits no scripts (self-host).
    """

    plugin_kind = "control"
    name = "htmx"

    def __init__(
        self,
        *,
        version: str = DEFAULT_VERSION,
        idiomorph: bool = True,
        sse: bool = False,
        cdn: bool = True,
        middleware: bool = False,
    ):
        if cdn and version not in PINNED_SCRIPTS:
            raise ValueError(
                f"htmx {version!r} has no pinned integrity hash; use one of "
                f"{sorted(PINNED_SCRIPTS)} or cdn=False and host the file yourself"
            )
        self.version = version
        self.idiomorph = idiomorph
        self.sse = sse
        self.cdn = cdn
        self.middleware = middleware

    def artifacts(self):
        """CDN-only — no files to ship."""
        return ()

    def document_head(self) -> Sequence[Any]:
        return ()

    def document_body(self) -> Sequence[Any]:
        if not self.cdn:
            return []
        files = PINNED_SCRIPTS[self.version]
        body = [_pinned_script(files["htmx"])]
        if self.idiomorph:
            body.append(_pinned_script(IDIOMORPH_SCRIPT))
        if self.sse:
            body.append(_pinned_script(files["sse"]))
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
