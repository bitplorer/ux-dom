"""Shared assertions for the example apps."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

# Dynamic generator, cannot carry an integrity hash; dev galleries only.
NO_SRI_ALLOWED = ("https://cdn.tailwindcss.com",)


def client(app) -> TestClient:
    return TestClient(app)


def csp_nonce(response) -> str:
    header = response.headers["content-security-policy"]
    match = re.search(r"'nonce-([^']+)'", header)
    assert match, header
    return match.group(1)


def external_scripts(html: str) -> list[str]:
    return re.findall(r"<script\b[^>]*\bsrc=\"https?://[^>]*>", html)


def assert_external_scripts_pinned(html: str) -> None:
    """Every third-party <script src> carries SRI + crossorigin."""
    for tag in external_scripts(html):
        if any(host in tag for host in NO_SRI_ALLOWED):
            continue
        assert 'integrity="sha384-' in tag, tag
        assert 'crossorigin="anonymous"' in tag, tag


def assert_scripts_nonced(response) -> None:
    nonce = csp_nonce(response)
    tags = re.findall(r"<script\b[^>]*>", response.text)
    assert tags, "no scripts"
    for tag in tags:
        assert f'nonce="{nonce}"' in tag, tag


def compact(html: str) -> str:
    """Drop the pretty-printer's whitespace around tags."""
    return re.sub(r"\s*(<[^>]+>)\s*", r"\1", html)


HTMX_CONFIG = (
    '<meta content="{&quot;includeIndicatorStyles&quot;:false}" name="htmx-config">'
)


def assert_htmx_csp_safe(html: str) -> None:
    """htmx injects an inline <style> for indicators unless told not to; a
    nonce CSP blocks it (style-src-elem). Pages with htmx under Csp opt out."""
    assert HTMX_CONFIG in html, "missing htmx-config includeIndicatorStyles=false"
