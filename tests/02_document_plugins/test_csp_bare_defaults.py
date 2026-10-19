"""Bare Csp() matches Csp.prod() on script inline and connect-src.

Csp.dev() stays the permissive DX preset.
"""

from __future__ import annotations

from ux_dom.plugins.csp import (
    Csp,
    CspMiddleware,
    CspPolicy,
    build_csp_header,
    policy_dev,
)

# Golden header for Csp.dev() / policy_dev() at nonce "N" (pinned before the
# bare-default tightening). Hosts, style unsafe-inline, script unsafe-inline,
# and bare ws:/wss: are part of the DX preset.
_DEV_HEADER = (
    "default-src 'self'; "
    "script-src 'nonce-N' 'strict-dynamic' https://unpkg.com "
    "https://cdn.jsdelivr.net https://cdn.tailwindcss.com 'unsafe-inline'; "
    "style-src 'nonce-N' 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self' ws: wss:; "
    "font-src 'self' data:; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "style-src-attr 'unsafe-inline'"
)


def _directives(header: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for part in header.split(";"):
        part = part.strip()
        if not part:
            continue
        name, _, value = part.partition(" ")
        found[name] = value
    return found


def _script_src_without_hosts(value: str) -> str:
    """Drop host allowlists so script-src comparison is the safety tokens."""
    tokens = [
        token
        for token in value.split()
        if not token.startswith(("http://", "https://"))
    ]
    return " ".join(tokens)


def test_bare_csp_defaults_match_prod_on_script_and_connect():
    """Csp(), CspPolicy, CspMiddleware, and build_csp_header are prod-safe.

    No legacy script 'unsafe-inline', and connect-src is 'self' only.
    Those header directives match Csp.prod() (script-src compared without
    host allowlists, which bare Csp() may still list).
    """
    bare = Csp()
    assert bare.script_unsafe_inline_legacy is False
    assert list(bare.connect_src) == ["'self'"]

    policy = CspPolicy()
    assert policy.script_unsafe_inline_legacy is False
    assert policy.connect_src == ("'self'",)

    middleware = CspMiddleware(app=None)
    assert middleware.policy.script_unsafe_inline_legacy is False
    assert middleware.policy.connect_src == ("'self'",)

    built = _directives(build_csp_header("N"))
    assert "'unsafe-inline'" not in built["script-src"]
    assert built["connect-src"] == "'self'"

    bare_header = _directives(bare.to_policy().build("N"))
    prod_header = _directives(Csp.prod().to_policy().build("N"))
    assert bare_header["connect-src"] == prod_header["connect-src"]
    assert _script_src_without_hosts(
        bare_header["script-src"]
    ) == _script_src_without_hosts(prod_header["script-src"])


def test_csp_dev_is_unchanged():
    """Csp.dev() keeps CDN hosts, style unsafe-inline, and bare ws:/wss:."""
    dev = Csp.dev()
    assert dev.script_unsafe_inline_legacy is True
    assert dev.style_unsafe_inline is True
    assert list(dev.connect_src) == ["'self'", "ws:", "wss:"]
    assert list(dev.script_hosts) == [
        "https://unpkg.com",
        "https://cdn.jsdelivr.net",
        "https://cdn.tailwindcss.com",
    ]
    assert dev.upgrade_insecure is False
    assert dev.to_policy().build("N") == _DEV_HEADER
    assert policy_dev().build("N") == _DEV_HEADER
