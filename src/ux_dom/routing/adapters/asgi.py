"""Pure ASGI adapter — DirectoryRoutes without FastAPI/Starlette.

Mount under any server::

    from ux_dom.routing.core import DirectoryRoutes
    from ux_dom.routing.adapters.asgi import DirectoryASGI

    core = DirectoryRoutes(PACKAGE, hooks=hooks)
    core.discover()
    app = DirectoryASGI(core)
    # uvicorn app:app
"""
from __future__ import annotations

import re
from typing import Any, Callable, Optional
from urllib.parse import unquote

from ux_dom.routing.core import DirectoryRoutes, RouteRecord, RouterHooks

__all__ = ["DirectoryASGI", "match_record"]


def _compile_path(path: str) -> tuple[re.Pattern[str], list[str]]:
    names: list[str] = []
    parts = []
    for seg in path.strip("/").split("/"):
        if not seg:
            continue
        if seg.startswith("{") and seg.endswith("}"):
            name = seg[1:-1]
            names.append(name)
            parts.append(r"(?P<%s>[^/]+)" % re.escape(name))
        else:
            parts.append(re.escape(seg))
    if not parts:
        return re.compile(r"^/?$"), names
    return re.compile(r"^/" + "/".join(parts) + r"/?$"), names


def match_record(
    records: list[RouteRecord],
    method: str,
    path: str,
) -> Optional[tuple[RouteRecord, dict[str, str]]]:
    method_u = method.upper()
    path = unquote(path or "/")
    if not path.startswith("/"):
        path = "/" + path
    for rec in records:
        if rec.method.upper() != method_u and not (
            method_u == "HEAD" and rec.method.upper() == "GET"
        ):
            continue
        if rec.path == path or rec.path.rstrip("/") == path.rstrip("/"):
            return rec, {}
        if "{" in rec.path:
            rx, names = _compile_path(rec.path)
            m = rx.match(path)
            if m:
                return rec, {k: unquote(v) for k, v in m.groupdict().items()}
    return None


def _invoke(rec: RouteRecord, hooks: RouterHooks, path_params: dict) -> Any:
    resolve = hooks.resolve_unit if hooks else None
    if rec.kind == "explicit" and rec.handler is not None:
        handler = rec.handler
        try:
            return handler(**path_params) if path_params else handler()
        except TypeError:
            return handler()
    page_cls = rec.page_cls
    if page_cls is None:
        return None
    inst = None
    if resolve is not None:
        try:
            inst = resolve(page_cls, rec.path, rec.name)
        except Exception:
            inst = None
    if inst is None:
        try:
            inst = page_cls()
        except Exception:
            return None
    render = getattr(inst, "render", None) or getattr(inst, "__render__", None)
    if callable(render):
        try:
            return render(**path_params) if path_params else render()
        except TypeError:
            return render()
    return inst


def _body_bytes(result: Any) -> bytes:
    try:
        from ux_dom.response.serialize import to_html_bytes

        return to_html_bytes(result)
    except Exception:
        if result is None:
            return b""
        if isinstance(result, (bytes, bytearray)):
            return bytes(result)
        return str(result).encode("utf-8")


class DirectoryASGI:
    """Pure ASGI application over :class:`DirectoryRoutes`.

    No FastAPI / Starlette imports. Uses domain ``to_html_bytes`` for body.
    """

    def __init__(self, core: DirectoryRoutes) -> None:
        if not core.records:
            core.discover()
        self.core = core
        self.hooks = core.hooks or RouterHooks()
        self._records = list(core.records)

    @property
    def route_table(self) -> list:
        return self.core.route_table()

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await send({"type": "http.response.start", "status": 404, "headers": []})
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "/") or "/"
        hit = match_record(self._records, method, path)
        if hit is None:
            body = b"Not Found"
            await send(
                {
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [
                        (b"content-type", b"text/plain; charset=utf-8"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body, "more_body": False})
            return

        rec, params = hit
        try:
            result = _invoke(rec, self.hooks, params)
            body = _body_bytes(result)
            status = 200
        except Exception as exc:
            body = ("Error: %s" % exc).encode("utf-8", "replace")
            status = 500

        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"text/html; charset=utf-8"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})
