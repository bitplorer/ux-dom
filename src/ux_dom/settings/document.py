# Copyright (c) 2022-2026 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Document — **single source of truth** for the HTML shell.

Architecture
------------
::

    document = Document(head=…, body=[])
    document.use(XElement(), Htmx(), Csp.auto())   # runtimes → tags + mount hooks
    app = FastAPI(...)
    document.mount(app)                            # static + middleware from runtimes
            │
            ▼
    HtmlDocument  — two-stage head/body order (call-time then common_*)

Rules
-----
* **Document** owns ``<head>`` / ``<body>`` placement and runtime tags.
* **FastAPI** owns the process (routes, servers).
* **App / PluginHub** are optional registries for tests / advanced hubs.
* ``include_runtimes=True`` only merges an optional hub into common_*; normal apps
  put everything on ``document.use`` and leave this flag off.
"""

from __future__ import annotations

import typing as T
from dataclasses import dataclass, field

from ux_dom.dom.htmldocument import HtmlDocument
from ux_dom.dom.src import ext

__all__ = [
    "Document",
    "ProductAssetsMoved",
    "WebAssets",
]


def _as_list(value: T.Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return [value]


@dataclass
class Document(object):
    """
    Two-stage HTML shell — **order is deliberate** (see HtmlDocument.render).

    Stage A — construction (``Document(head=…, body=…)``)
        Stored as **common_head** / **common_body**.

    Stage B — call (``doc(*content, head=…, body=…)``)
        Page-specific **head** / **body** for this response.

    Placement inside ``<html>`` (do not “flatten” this away)::

        <head>
          [B] call-time head     ← page title, page CSS, one-off tags
          [A] common_head       ← shared meta defaults, XElement, etc.
        </head>
        <body>
          *content              ← page components
          [B] call-time body    ← page-only body assets
          placeholders          ← Body / XElement definition slots
          [A] common_body       ← shared end-of-body scripts (HTMX, …)
        </body>

    So shared scripts that must run **after** content belong in **init body**
    (common_body). Shared head scripts that should follow page meta belong in
    **init head** (common_head). Page title/CSS belong in **call head**.

    Callables in any of the four lists are invoked at call time::

        Document(head=[lambda ctx: meta(property="csp", content=ctx["csp"])])
        doc(page, head=[title("Hi")])

    ``ctx`` includes ``nonce`` (from CSP middleware), ``document``, and kwargs.
    Runtimes attach on the **instance** (``document.use``), not the class::

        document = Document(head=[...]).use(XElement(), Htmx())  # shared shell
        document.using(Alpine())(*page)  # page-only extra, does not mutate shared
        document(*page, use=[Alpine()])  # same idea at call time

    Runtimes always feed **common_** head/body (stage A), never call-time lists.
    """

    head: T.Optional[T.Union[ext.Tags, list[ext.Tags], T.Callable]] = None
    body: T.Optional[T.Union[ext.Tags, list[ext.Tags], T.Callable]] = None
    ensure_csrf_token: bool = field(default=False)
    include_runtimes: bool = False  # optional hub merge into common_* only
    hub: T.Any = None
    plugins: T.Optional[bool] = None
    plugin_hub: T.Any = None
    _runtimes: list = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.plugins is not None:
            self.include_runtimes = bool(self.plugins)
        if self.plugin_hub is not None and self.hub is None:
            self.hub = self.plugin_hub
        if not isinstance(self._runtimes, list):
            self._runtimes = list(self._runtimes or [])

    # ── runtimes → stage A (common_head / common_body) only ───────────────

    def use(self, *runtimes: T.Any) -> "Document":
        """
        Attach runtimes on **this instance** (mutates shared shell).

        Prefer for app-wide needs on the module-level ``document``.
        For one page only, use ``.using(...)`` or ``doc(..., use=[...])``.
        """
        for rt in runtimes:
            if rt is None:
                continue
            self._validate_runtime(rt)
            name = getattr(rt, "name", None) or type(rt).__name__
            self._runtimes = [
                r
                for r in self._runtimes
                if (getattr(r, "name", None) or type(r).__name__) != name
            ]
            self._runtimes.append(rt)
        return self

    def using(self, *runtimes: T.Any) -> "Document":
        """Return a copy with extra runtimes; do not mutate this instance.

        Use for page-specific needs while keeping a shared module-level shell::

            document.using(Channel.optional())(page, head=[title("Live")])

        Equivalent call form: ``document(page, use=[Channel.optional()])``.
        """
        child = self.copy()
        child.use(*runtimes)
        return child

    def copy(self) -> "Document":
        """Shallow-copy head/body lists and the runtime list.

        Runtime *objects* are shared by reference; the list itself is new so
        ``use`` on the copy does not change the parent.
        """
        return type(self)(
            head=list(self.head) if isinstance(self.head, list) else self.head,
            body=list(self.body) if isinstance(self.body, list) else self.body,
            ensure_csrf_token=self.ensure_csrf_token,
            include_runtimes=self.include_runtimes,
            hub=self.hub,
            _runtimes=list(self._runtimes),
        )

    def _validate_runtime(self, rt: T.Any) -> None:
        name = getattr(rt, "name", None)
        if name is not None and not str(name).strip():
            raise ValueError(f"runtime {type(rt)!r} has empty name")
        has_surface = any(
            callable(getattr(rt, attr, None))
            for attr in (
                "document_head",
                "document_body",
                "mount",
                "served_files",
                "artifacts",
                "wire",
            )
        )
        if not has_surface:
            raise TypeError(
                f"{type(rt)!r} is not a Document runtime — expected "
                f"document_head/document_body/mount/served_files"
            )

    def runtimes(self) -> list:
        return list(self._runtimes)

    def clear_runtimes(self) -> "Document":
        self._runtimes.clear()
        return self

    @classmethod
    def for_app(
        cls,
        app: T.Any = None,
        *,
        head: T.Any = None,
        body: T.Any = None,
        hub: T.Any = None,
        **kwargs: T.Any,
    ) -> "Document":
        h = hub
        if h is None and app is not None:
            h = getattr(app, "hub", None)
        return cls(head=head, body=body, include_runtimes=True, hub=h, **kwargs)

    def _runtime_common_head_body(self) -> tuple[list, list]:
        """Runtime tags for stage A only (common_head / common_body)."""
        head: list = []
        body: list = []
        for rt in self._runtimes:
            arts = getattr(rt, "artifacts", None)
            if callable(arts):
                for a in arts() or ():
                    node = getattr(a, "html_node", lambda: None)()
                    if node is None:
                        continue
                    inj = getattr(a, "inject", "none")
                    if inj == "head":
                        head.append(node)
                    elif inj == "body":
                        body.append(node)
            if callable(getattr(rt, "document_head", None)):
                head.extend(list(rt.document_head() or ()))
            if callable(getattr(rt, "document_body", None)):
                body.extend(list(rt.document_body() or ()))
        if self.include_runtimes:
            try:
                from ux_dom.plugins.hub import get_hub

                hub = self.hub if self.hub is not None else get_hub()
                hh, bb = hub.shell_fragments()
                head.extend(hh)
                body.extend(bb)
            except Exception:
                pass
        try:
            from ux_dom.plugins.dedupe import dedupe_dom_nodes

            head = dedupe_dom_nodes(head)
            body = dedupe_dom_nodes(body)
        except Exception:
            pass
        return head, body

    def runtime_tags(self) -> tuple[list, list]:
        return self._runtime_common_head_body()

    def plugin_head_body(self) -> tuple[list, list]:
        return self.runtime_tags()

    # ── evaluate callables + CSP stamp at the right moment ────────────────

    def _call_ctx(self, **kwargs: T.Any) -> dict:
        try:
            from ux_dom.plugins.csp import get_nonce

            nonce = get_nonce()
        except Exception:
            nonce = ""
        return {
            "document": self,
            "nonce": nonce,
            **kwargs,
        }

    @staticmethod
    def _is_stage_hook(obj: T.Any) -> bool:
        """Lambdas/functions only — never dom_tag (tags are also callable)."""
        if obj is None or isinstance(obj, type):
            return False
        try:
            from ux_dom.dom.src.dom_tag import dom_tag

            if isinstance(obj, dom_tag):
                return False
        except Exception:
            pass
        # Components / Tags often have attributes+children
        if hasattr(obj, "attributes") and hasattr(obj, "children"):
            return False
        import types
        from functools import partial

        return isinstance(obj, (types.FunctionType, types.MethodType, partial)) or (
            callable(obj)
            and getattr(obj, "__module__", None) not in (None,)
            and type(obj).__name__ in ("function", "method", "partial", "staticmethod")
        )

    def _eval_list(self, items: T.Any, ctx: dict) -> list:
        """Expand list/tuple; invoke stage hooks only; keep tags/strings/dicts."""
        if items is None:
            return []
        if self._is_stage_hook(items):
            try:
                items = items(ctx)
            except TypeError:
                items = items()
        seq = items if isinstance(items, (list, tuple)) else [items]
        out: list = []
        for item in seq:
            if item is None:
                continue
            if self._is_stage_hook(item):
                try:
                    item = item(ctx)
                except TypeError:
                    item = item()
                if item is None:
                    continue
                if isinstance(item, (list, tuple)):
                    out.extend(x for x in item if x is not None)
                    continue
            out.append(item)
        return out

    def _stamp_if_nonce(self, nodes: list) -> list:
        try:
            from ux_dom.plugins.csp import get_nonce, stamp_nonce

            if get_nonce():
                return stamp_nonce(nodes)
        except Exception:
            pass
        return nodes

    def resolved_head(self) -> list:
        """Debug: common_head only (stage A), not call-time head."""
        rt_h, _ = self._runtime_common_head_body()
        return _as_list(self.head) + list(rt_h)

    def resolved_body(self) -> list:
        """Debug: common_body only (stage A)."""
        _, rt_b = self._runtime_common_head_body()
        return _as_list(self.body) + list(rt_b)

    def mount(self, app: T.Any) -> T.Any:
        """Apply this document's runtimes to an ASGI app (startup only).

        Not part of head/body placement. For each attached runtime:

        1. ``served_files()`` → allowlisted static routes (``/ux-dom/static/…``)
        2. ``mount(app)`` → middleware (CSP, HTMX, …)

        Call once after ``FastAPI()`` is created. See ``docs/guides/DOCUMENT.md``.
        """
        if app is None:
            return app
        files = []
        for rt in self._runtimes:
            fn = getattr(rt, "served_files", None)
            if callable(fn):
                files.extend(list(fn() or ()))
            mount = getattr(rt, "mount", None)
            if callable(mount):
                try:
                    mount(app)
                except TypeError:
                    mount(app, hub=None)
        if files:
            try:
                from ux_dom.plugins.safe_static import install_safe_static

                install_safe_static(app, files)
            except Exception:
                pass
        return app

    def __call__(self, *args, head=None, body=None, use=None, **kwargs) -> HtmlDocument:
        """
        Stage B: page content + optional call-time head/body.

        ``use=`` — extra runtimes for **this response only** (not stored on self).
        Same placement rules as ``.use`` (common_head / common_body).

        Preserves HtmlDocument order — does **not** merge call lists into common.
        """
        kwargs.setdefault("ensure_csrf_token", self.ensure_csrf_token)
        target = self
        if use is not None:
            extra = use if isinstance(use, (list, tuple)) else (use,)
            target = self.using(*extra)

        ctx = target._call_ctx(
            **{k: v for k, v in kwargs.items() if k != "ensure_csrf_token"}
        )

        # Stage A — common_* (init head/body + instance runtimes [+ page use=])
        rt_head, rt_body = target._runtime_common_head_body()
        common_head = target._eval_list(target.head, ctx) + target._eval_list(
            rt_head, ctx
        )
        common_body = target._eval_list(target.body, ctx) + target._eval_list(
            rt_body, ctx
        )

        # Stage B — call-time head/body (page-specific)
        call_head = self._eval_list(head, ctx)
        call_body = self._eval_list(body, ctx)

        # CSP nonce on script/style at the moment of placement
        common_head = self._stamp_if_nonce(common_head)
        common_body = self._stamp_if_nonce(common_body)
        call_head = self._stamp_if_nonce(call_head)
        call_body = self._stamp_if_nonce(call_body)

        return HtmlDocument(
            *args,
            head=call_head if call_head else None,
            body=call_body if call_body else None,
            common_head=common_head if common_head else None,
            common_body=common_body if common_body else None,
            **kwargs,
        )


_ASSETS_TEACH = (
    "WebAssets is product app layout, not a Document API. "
    "Use: from ux_compose import WebAssets  "
    "(create-app / build / /css mount live on ux-compose). "
    "ux-dom keeps className, Document <link>, and package static "
    "/ux-dom/static/x_element.js."
)


class ProductAssetsMoved(RuntimeError):
    """Raised when a caller constructs app asset layout from ux-dom."""

    def __init__(self, message: str = _ASSETS_TEACH):
        super().__init__(message)


class WebAssets:
    """Fail-closed. App folders are ``ux_compose.assets.WebAssets``."""

    def __init__(self, *args, **kwargs):
        raise ProductAssetsMoved()
