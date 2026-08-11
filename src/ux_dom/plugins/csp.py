# Copyright (c) 2026 ux-dom
"""
CSP nonces — **one place, least confusion: middleware**.

Read-agnostic secure nonce
--------------------------
The nonce is a cryptographically strong, **per-request** secret. After the
middleware creates it, you can resolve it from **any** of these sources
(first hit wins) — you do not care which "read path" you are on:

1. **Explicit** argument (best for workers / tests)
2. **ContextVar** (async request Task / sync Context)
3. **ASGI ``scope["ux_dom_csp_nonce"]``** (always set by middleware)
4. **``request.state.ux_dom_csp_nonce``** when Starlette Request exists

**Stamp once on the request Task**, then the nonce is **baked into**
``script`` / ``style`` attributes. Serialize (pretty worker, compact stream)
only reads the tree — **no ContextVar required** after stamp.

::

    # app shell
    document.use(Csp())   # or App().use(Csp())

    # boundary (HTMLResponse / StreamingResponse already do this)
    n = resolve_nonce(scope=scope)   # or get_nonce()
    stamp_tree(doc, n)               # bake into DOM
    # stream/render — worker-safe, read-agnostic
"""

from __future__ import annotations

import re
import secrets
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Sequence

# ── secure generation ─────────────────────────────────────────────────────

# 32 bytes → ~43 urlsafe chars; unguessable for CSP nonce budgets.
_NONCE_BYTES = 32


def generate_nonce(nbytes: int = _NONCE_BYTES) -> str:
    """Cryptographically secure nonce (url-safe, no padding surprises)."""
    if nbytes < 16:
        raise ValueError("CSP nonce must be at least 16 bytes of entropy")
    return secrets.token_urlsafe(nbytes)


# ── request-scoped storage (multiple mirrors = read-agnostic) ─────────────

_csp_nonce: ContextVar[str] = ContextVar("ux_dom_csp_nonce", default="")


def get_nonce() -> str:
    """ContextVar read (request Task / current Context). May be empty off-request."""
    return _csp_nonce.get() or ""


def set_nonce(nonce: str) -> Token:
    if not nonce or not isinstance(nonce, str):
        raise ValueError("nonce must be a non-empty str")
    return _csp_nonce.set(nonce)


def reset_nonce(token: Token) -> None:
    """Reset ContextVar; tolerate cross-Context tokens (ASGI stream end).

    Starlette/TestClient may finish the body in a different Context than
    the one that called ``set_nonce``. ``Token.reset`` then raises
    ``ValueError`` — fall back to clearing the current Context value.
    """
    try:
        _csp_nonce.reset(token)
    except ValueError:
        _csp_nonce.set("")


def clear_nonce() -> None:
    _csp_nonce.set("")


def resolve_nonce(
    nonce: Optional[str] = None,
    *,
    scope: Optional[dict] = None,
    request: Any = None,
    require: bool = False,
) -> str:
    """Read-agnostic nonce resolution (secure value, any transport).

    Order:
      1. explicit ``nonce=``
      2. ContextVar (``get_nonce()``)
      3. ``request.state.ux_dom_csp_nonce`` / ``request.scope``
      4. ``scope["ux_dom_csp_nonce"]``
      5. ``scope["state"]`` dict key if present

    After ``stamp_tree``, prefer reading attributes from the DOM — this
    helper is for **before** stamp / header construction.
    """
    if nonce:
        return str(nonce)

    n = get_nonce()
    if n:
        return n

    if request is not None:
        state = getattr(request, "state", None)
        if state is not None:
            for key in ("ux_dom_csp_nonce", "csp_nonce", "nonce"):
                val = getattr(state, key, None)
                if val:
                    return str(val)
                if isinstance(state, dict) and state.get(key):
                    return str(state[key])
        req_scope = getattr(request, "scope", None)
        if isinstance(req_scope, dict):
            n = _nonce_from_scope(req_scope)
            if n:
                return n

    if scope is not None:
        n = _nonce_from_scope(scope)
        if n:
            return n

    if require:
        raise RuntimeError(
            "CSP nonce not available — is Csp middleware installed, "
            "and are you on the request that set it?"
        )
    return ""


def _nonce_from_scope(scope: dict) -> str:
    n = scope.get("ux_dom_csp_nonce") or scope.get("csp_nonce")
    if n:
        return str(n)
    state = scope.get("state")
    if state is None:
        return ""
    if isinstance(state, dict):
        return str(state.get("ux_dom_csp_nonce") or state.get("csp_nonce") or "")
    for key in ("ux_dom_csp_nonce", "csp_nonce"):
        val = getattr(state, key, None)
        if val:
            return str(val)
    return ""


def bind_nonce_to_scope(scope: dict, nonce: str) -> None:
    """Mirror nonce onto ASGI scope (and state dict if present)."""
    scope["ux_dom_csp_nonce"] = nonce
    state = scope.get("state")
    if isinstance(state, dict):
        state["ux_dom_csp_nonce"] = nonce
    elif state is not None:
        try:
            setattr(state, "ux_dom_csp_nonce", nonce)
        except Exception:
            pass


# ── DOM / HTML stamping (bake nonce into tree → read-agnostic serialize) ──


def _set_attr(node: Any, key: str, value: str) -> Any:
    if node is None:
        return node
    attrs = getattr(node, "attributes", None)
    if isinstance(attrs, dict):
        attrs[key] = value
        try:
            node.set_attribute(key, value)
        except Exception:
            pass
        return node
    if isinstance(node, str):
        return _inject_nonce_html(node, value)
    return node


def _inject_nonce_html(html: str, nonce: str) -> str:
    def repl(m: re.Match[str]) -> str:
        tag = m.group(0)
        if re.search(r"\bnonce\s*=", tag, re.I):
            return tag
        if tag.endswith("/>"):
            return tag[:-2] + f' nonce="{nonce}" />'
        if tag.endswith(">"):
            return tag[:-1] + f' nonce="{nonce}">'
        return tag

    return re.sub(r"<(?:script|style)(\s[^>]*)?>", repl, html, flags=re.I)


def stamp_tree(
    node: Any,
    nonce: Optional[str] = None,
    *,
    scope: Optional[dict] = None,
    request: Any = None,
) -> Any:
    """Bake nonce into every ``script`` / ``style`` (in place).

    Prefer an explicit ``nonce`` (or ``resolve_nonce`` sources). After this,
    serialize does not need ContextVar — attributes are already on the nodes.
    """
    n = resolve_nonce(nonce, scope=scope, request=request)
    if not n or node is None:
        return node
    if isinstance(node, (list, tuple)):
        for child in node:
            stamp_tree(child, n)
        return node
    if isinstance(node, str):
        return _inject_nonce_html(node, n)

    tag = (
        getattr(node, "tagname", None)
        or getattr(node, "name", None)
        or type(node).__name__
        or ""
    ).lower()
    if tag in {"script", "style"}:
        _set_attr(node, "nonce", n)

    children = getattr(node, "children", None)
    if children:
        for child in list(children):
            stamp_tree(child, n)
    return node


def stamp_nonce(
    nodes: Iterable[Any] | Any,
    nonce: Optional[str] = None,
    *,
    tags: Sequence[str] = ("script", "style"),
    scope: Optional[dict] = None,
    request: Any = None,
) -> list[Any]:
    """Stamp a flat list of nodes (shell fragments)."""
    n = resolve_nonce(nonce, scope=scope, request=request)
    if nodes is None:
        return []
    seq = list(nodes) if isinstance(nodes, (list, tuple)) else [nodes]
    if not n:
        return seq
    tagset = {t.lower() for t in tags}
    out: list[Any] = []
    for node in seq:
        if isinstance(node, str):
            out.append(_inject_nonce_html(node, n))
            continue
        tag = (
            getattr(node, "tagname", None)
            or getattr(node, "name", None)
            or type(node).__name__
            or ""
        ).lower()
        if tag in tagset:
            out.append(_set_attr(node, "nonce", n))
        else:
            stamp_tree(node, n)
            out.append(node)
    return out


def build_csp_header(
    nonce: str,
    *,
    strict_dynamic: bool = True,
    script_hosts: Sequence[str] = (),
    style_hosts: Sequence[str] = (),
    style_unsafe_inline: bool = False,
    script_unsafe_inline_legacy: bool = True,
    img_src: Sequence[str] = ("'self'", "data:"),
    connect_src: Sequence[str] = ("'self'", "ws:", "wss:"),
    font_src: Sequence[str] = ("'self'", "data:"),
    frame_ancestors: str = "'none'",
    base_uri: str = "'self'",
    object_src: str = "'none'",
    form_action: str = "'self'",
    upgrade_insecure: bool = False,
    report_uri: Optional[str] = None,
    extra_directives: Optional[dict[str, str]] = None,
) -> str:
    """Build a ``Content-Security-Policy`` value for one response.

    See ``docs/security/CSP.md`` for how ``'strict-dynamic'`` interacts with host
    allowlists in modern vs legacy browsers.
    """
    if not nonce:
        raise ValueError("CSP header requires a non-empty nonce")

    script_parts = [f"'nonce-{nonce}'"]
    if strict_dynamic:
        script_parts.append("'strict-dynamic'")
    script_parts.extend(script_hosts)
    # Older Safari: unsafe-inline ignored once nonce/hash present (CSP3).
    if script_unsafe_inline_legacy:
        script_parts.append("'unsafe-inline'")

    style_parts = [f"'nonce-{nonce}'", "'self'", *style_hosts]
    if style_unsafe_inline:
        # Needed for element style="..." / many Tailwind+Alpine patterns.
        style_parts.append("'unsafe-inline'")

    directives: dict[str, str] = {
        "default-src": "'self'",
        "script-src": " ".join(script_parts),
        "style-src": " ".join(style_parts),
        "img-src": " ".join(img_src),
        "connect-src": " ".join(connect_src),
        "font-src": " ".join(font_src),
        "object-src": object_src,
        "base-uri": base_uri,
        "frame-ancestors": frame_ancestors,
        "form-action": form_action,
    }
    if upgrade_insecure:
        directives["upgrade-insecure-requests"] = ""
    if report_uri:
        directives["report-uri"] = report_uri
    if extra_directives:
        directives.update(extra_directives)

    parts = []
    for k, v in directives.items():
        parts.append(k if v == "" else f"{k} {v}")
    return "; ".join(parts)


# ── Policy presets (dev / prod / report-only) ─────────────────────────────

_DEFAULT_SCRIPT_HOSTS = (
    "https://unpkg.com",
    "https://cdn.jsdelivr.net",
    "https://cdn.tailwindcss.com",
)


@dataclass(frozen=True)
class CspPolicy:
    """Immutable CSP knobs shared by ``build_csp_header`` and middleware.

    Prefer factory helpers on ``Csp``::

        Csp.dev()   # create-app / CDN DX
        Csp.prod()  # self-hosted, tight
        Csp.report_only()  # observe without enforce
    """

    strict_dynamic: bool = True
    script_hosts: tuple = _DEFAULT_SCRIPT_HOSTS
    style_hosts: tuple = ()
    style_unsafe_inline: bool = False
    script_unsafe_inline_legacy: bool = True
    img_src: tuple = ("'self'", "data:")
    connect_src: tuple = ("'self'", "ws:", "wss:")
    font_src: tuple = ("'self'", "data:")
    frame_ancestors: str = "'none'"
    base_uri: str = "'self'"
    object_src: str = "'none'"
    form_action: str = "'self'"
    upgrade_insecure: bool = False
    report_uri: Optional[str] = None
    extra_directives: Optional[dict] = None
    report_only: bool = False
    debug_header: bool = False
    nonce_bytes: int = _NONCE_BYTES

    def header_kwargs(self) -> dict[str, Any]:
        return {
            "strict_dynamic": self.strict_dynamic,
            "script_hosts": list(self.script_hosts),
            "style_hosts": list(self.style_hosts),
            "style_unsafe_inline": self.style_unsafe_inline,
            "script_unsafe_inline_legacy": self.script_unsafe_inline_legacy,
            "img_src": list(self.img_src),
            "connect_src": list(self.connect_src),
            "font_src": list(self.font_src),
            "frame_ancestors": self.frame_ancestors,
            "base_uri": self.base_uri,
            "object_src": self.object_src,
            "form_action": self.form_action,
            "upgrade_insecure": self.upgrade_insecure,
            "report_uri": self.report_uri,
            "extra_directives": dict(self.extra_directives or {}),
        }

    def build(self, nonce: str) -> str:
        return build_csp_header(nonce, **self.header_kwargs())


def policy_dev(**overrides: Any) -> CspPolicy:
    """DX / create-app: CDN hosts + style unsafe-inline for Tailwind/Alpine."""
    base = CspPolicy(
        strict_dynamic=True,
        script_hosts=_DEFAULT_SCRIPT_HOSTS,
        style_unsafe_inline=True,  # style="..." + Tailwind CDN patterns
        connect_src=("'self'", "ws:", "wss:"),
        debug_header=False,
    )
    if overrides:
        return CspPolicy(**{**base.__dict__, **overrides})
    return base


def policy_prod(**overrides: Any) -> CspPolicy:
    """Production: no CDN hosts, tight connect, form-action, optional HSTS-ish upgrade."""
    base = CspPolicy(
        strict_dynamic=True,
        script_hosts=(),  # self-host via package static / SafeStatic
        style_hosts=(),
        style_unsafe_inline=False,  # prefer nonced <style> only
        connect_src=("'self'", "ws:", "wss:"),  # tighten hosts in overrides
        form_action="'self'",
        upgrade_insecure=True,
        frame_ancestors="'none'",
        extra_directives={
            # Optional hardening; override empty dict to drop
            "worker-src": "'self'",
        },
    )
    if overrides:
        return CspPolicy(**{**base.__dict__, **overrides})
    return base


def policy_report_only(**overrides: Any) -> CspPolicy:
    """Same as prod knobs but ``Content-Security-Policy-Report-Only`` header."""
    base = policy_prod(report_only=True, upgrade_insecure=False)
    if overrides:
        return CspPolicy(**{**base.__dict__, **overrides})
    return base


# ── ASGI middleware (stream-safe) ─────────────────────────────────────────


class CspMiddleware:
    """
    Pure ASGI middleware — single owner of nonce lifecycle.

    Writes the same secure nonce to:
      * ContextVar (``get_nonce`` / ``resolve_nonce``)
      * ``scope["ux_dom_csp_nonce"]`` (read-agnostic for any layer)
    Then attaches CSP (or CSP-Report-Only) and clears ContextVar when done.
    """

    def __init__(
        self,
        app: Any,
        *,
        policy: Optional[CspPolicy] = None,
        # flat kwargs accepted by App.use(Csp(...))
        strict_dynamic: bool = True,
        script_hosts: Sequence[str] = (),
        style_hosts: Sequence[str] = (),
        style_unsafe_inline: bool = False,
        script_unsafe_inline_legacy: bool = True,
        connect_src: Sequence[str] = ("'self'", "ws:", "wss:"),
        img_src: Sequence[str] = ("'self'", "data:"),
        font_src: Sequence[str] = ("'self'", "data:"),
        frame_ancestors: str = "'none'",
        base_uri: str = "'self'",
        object_src: str = "'none'",
        form_action: str = "'self'",
        upgrade_insecure: bool = False,
        report_uri: Optional[str] = None,
        extra_directives: Optional[dict[str, str]] = None,
        report_only: bool = False,
        debug_header: bool = False,
        nonce_bytes: int = _NONCE_BYTES,
    ) -> None:
        self.app = app
        if policy is not None:
            self.policy = policy
        else:
            self.policy = CspPolicy(
                strict_dynamic=strict_dynamic,
                script_hosts=tuple(script_hosts),
                style_hosts=tuple(style_hosts),
                style_unsafe_inline=style_unsafe_inline,
                script_unsafe_inline_legacy=script_unsafe_inline_legacy,
                connect_src=tuple(connect_src),
                img_src=tuple(img_src),
                font_src=tuple(font_src),
                frame_ancestors=frame_ancestors,
                base_uri=base_uri,
                object_src=object_src,
                form_action=form_action,
                upgrade_insecure=upgrade_insecure,
                report_uri=report_uri,
                extra_directives=dict(extra_directives or {}) or None,
                report_only=report_only,
                debug_header=debug_header,
                nonce_bytes=nonce_bytes,
            )

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        pol = self.policy
        nonce = generate_nonce(pol.nonce_bytes)
        token = set_nonce(nonce)
        bind_nonce_to_scope(scope, nonce)

        header_value = pol.build(nonce)
        header_name = (
            b"content-security-policy-report-only"
            if pol.report_only
            else b"content-security-policy"
        )
        header_name_str = header_name.decode("latin-1")
        done = False

        async def send_wrapper(message: dict) -> None:
            nonlocal done
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                existing = {
                    k.decode("latin-1").lower()
                    for k, _ in headers
                    if isinstance(k, (bytes, bytearray))
                }
                # Do not overwrite either enforce or report-only if already set
                if (
                    header_name_str not in existing
                    and "content-security-policy" not in existing
                    and "content-security-policy-report-only" not in existing
                ):
                    headers.append((header_name, header_value.encode("latin-1")))
                if pol.debug_header:
                    headers.append((b"x-ux_dom-csp-nonce", nonce.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)
            if message["type"] == "http.response.body" and not message.get(
                "more_body", False
            ):
                if not done:
                    done = True
                    reset_nonce(token)

        try:
            await self.app(scope, receive, send_wrapper)
        except BaseException:
            if not done:
                reset_nonce(token)
            raise
        else:
            if not done:
                reset_nonce(token)


# ── Plugin ────────────────────────────────────────────────────────────────


@dataclass
class Csp:
    """
    **The** CSP plugin — installs middleware. One line, no other wiring.

    ::

        document.use(Csp())           # same as Csp.dev() defaults
        document.use(Csp.dev())
        document.use(Csp.prod())
        document.use(Csp.report_only())

    Full knobs (also on ``CspPolicy``) are forwarded to middleware.
    """

    plugin_kind: str = "control"
    name: str = "csp"
    # core
    strict_dynamic: bool = True
    script_hosts: Sequence[str] = field(
        default_factory=lambda: list(_DEFAULT_SCRIPT_HOSTS)
    )
    style_hosts: Sequence[str] = field(default_factory=tuple)
    style_unsafe_inline: bool = False
    script_unsafe_inline_legacy: bool = True
    connect_src: Sequence[str] = field(
        default_factory=lambda: ["'self'", "ws:", "wss:"]
    )
    img_src: Sequence[str] = field(default_factory=lambda: ["'self'", "data:"])
    font_src: Sequence[str] = field(default_factory=lambda: ["'self'", "data:"])
    frame_ancestors: str = "'none'"
    base_uri: str = "'self'"
    object_src: str = "'none'"
    form_action: str = "'self'"
    upgrade_insecure: bool = False
    report_uri: Optional[str] = None
    extra_directives: Optional[dict[str, str]] = None
    is_report_only: bool = False
    enabled: bool = True
    debug_header: bool = False
    nonce_bytes: int = _NONCE_BYTES
    # optional prebuilt policy wins over flat fields when set
    policy: Optional[CspPolicy] = None

    # ── presets ──────────────────────────────────────────────────────────

    @classmethod
    def auto(cls, debug: Optional[bool] = None, **overrides: Any) -> "Csp":
        """Pick dev vs prod from DEBUG (env or argument) — zero-choice DX.

        * ``debug=True`` / ``DEBUG=1`` → :meth:`dev` (CDN + style attrs OK)
        * ``debug=False`` / ``DEBUG=0`` → :meth:`prod` (lock-down)

        Scaffold uses this so apps get CSP without learning presets first.
        """
        import os

        if debug is None:
            debug = os.environ.get("DEBUG", "1") not in ("0", "false", "False")
        return cls.dev(**overrides) if debug else cls.prod(**overrides)

    @classmethod
    def dev(cls, **overrides: Any) -> "Csp":
        """Create-app / local DX: CDNs + style unsafe-inline."""
        pol = policy_dev(**overrides)
        return cls.from_policy(pol)

    @classmethod
    def prod(cls, **overrides: Any) -> "Csp":
        """Production lock-down: no CDN script hosts, nonced styles preferred."""
        pol = policy_prod(**overrides)
        return cls.from_policy(pol)

    @classmethod
    def report_only(cls, **overrides: Any) -> "Csp":
        """Emit ``Content-Security-Policy-Report-Only`` (observe, don't block)."""
        pol = policy_report_only(**overrides)
        return cls.from_policy(pol)

    @classmethod
    def from_policy(cls, policy: CspPolicy) -> "Csp":
        return cls(
            strict_dynamic=policy.strict_dynamic,
            script_hosts=list(policy.script_hosts),
            style_hosts=list(policy.style_hosts),
            style_unsafe_inline=policy.style_unsafe_inline,
            script_unsafe_inline_legacy=policy.script_unsafe_inline_legacy,
            connect_src=list(policy.connect_src),
            img_src=list(policy.img_src),
            font_src=list(policy.font_src),
            frame_ancestors=policy.frame_ancestors,
            base_uri=policy.base_uri,
            object_src=policy.object_src,
            form_action=policy.form_action,
            upgrade_insecure=policy.upgrade_insecure,
            report_uri=policy.report_uri,
            extra_directives=dict(policy.extra_directives or {}) or None,
            is_report_only=policy.report_only,
            debug_header=policy.debug_header,
            nonce_bytes=policy.nonce_bytes,
            policy=policy,
        )

    def to_policy(self) -> CspPolicy:
        if self.policy is not None:
            return self.policy
        return CspPolicy(
            strict_dynamic=self.strict_dynamic,
            script_hosts=tuple(self.script_hosts),
            style_hosts=tuple(self.style_hosts),
            style_unsafe_inline=self.style_unsafe_inline,
            script_unsafe_inline_legacy=self.script_unsafe_inline_legacy,
            connect_src=tuple(self.connect_src),
            img_src=tuple(self.img_src),
            font_src=tuple(self.font_src),
            frame_ancestors=self.frame_ancestors,
            base_uri=self.base_uri,
            object_src=self.object_src,
            form_action=self.form_action,
            upgrade_insecure=self.upgrade_insecure,
            report_uri=self.report_uri,
            extra_directives=dict(self.extra_directives or {}) or None,
            report_only=self.is_report_only,
            debug_header=self.debug_header,
            nonce_bytes=self.nonce_bytes,
        )

    def artifacts(self) -> Sequence[Any]:
        return ()

    def document_head(self) -> Sequence[Any]:
        return ()

    def document_body(self) -> Sequence[Any]:
        return ()

    def wire(self, action: Any = None, **kwargs: Any) -> dict[str, Any]:
        return {}

    def partial_policy(self, request: Any) -> str:
        return "full"

    def mount(self, app: Any, **kwargs: Any) -> None:
        if not self.enabled or app is None:
            return
        app.add_middleware(CspMiddleware, policy=self.to_policy())


CspNonce = Csp


def shell_fragments_nonced(
    hub: Any = None,
    *extra_head: Any,
    extra_body: Sequence[Any] = (),
    dedupe: bool = True,
) -> tuple[list[Any], list[Any]]:
    """Explicit helper; normal ``shell_fragments`` already stamps when nonce is set."""
    from ux_dom.plugins.shell import shell_fragments

    head, body = shell_fragments(hub, *extra_head, extra_body=extra_body, dedupe=dedupe)
    return stamp_nonce(head), stamp_nonce(body)
