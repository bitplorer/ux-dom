# Copyright (c) 2026 ux-dom
"""Deduplicate script/link tags by src/href — prevent double injection."""

from __future__ import annotations

import re
from typing import Any, Iterable, List

# Match src= or href= in rendered HTML (attribute order varies)
_SRC_HREF = re.compile(r"""(?i)\b(?:src|href)\s*=\s*["']([^"']+)["']""")


def resource_key(node: Any) -> str | None:
    """
    Stable key for a DOM node if it loads an external resource.

    Returns normalized URL string, or None if node is not a script/link resource
    (inline scripts, plain divs, etc. are never deduped against each other).
    """
    if node is None:
        return None
    # Prefer attribute access on ux_dom tags
    attrs = getattr(node, "attributes", None) or getattr(node, "attrs", None)
    tag = getattr(node, "tagname", None) or getattr(node, "name", None) or ""
    tag = str(tag).lower()

    if isinstance(attrs, dict):
        src = attrs.get("src") or attrs.get("href")
        if src:
            return _norm(str(src))
        # some trees store without namespace
    # kwargs-style
    for key in ("src", "href"):
        if hasattr(node, key):
            val = getattr(node, key)
            if val:
                return _norm(str(val))

    # Fall back to rendered HTML (covers raw strings / HtmlFragment)
    html = str(node)
    if not html:
        return None
    # Only dedupe script/link-like strings
    low = html.lower().lstrip()
    if not (
        low.startswith("<script")
        or low.startswith("<link")
        or "src=" in low
        or "href=" in low
    ):
        # raw string of only a script tag from channel
        if "<script" not in low and "<link" not in low:
            return None
    m = _SRC_HREF.search(html)
    if m:
        return _norm(m.group(1))
    return None


def _norm(url: str) -> str:
    u = url.strip()
    # ignore fragment-only differences
    if "#" in u:
        u = u.split("#", 1)[0]
    return u


def dedupe_dom_nodes(nodes: Iterable[Any]) -> List[Any]:
    """Keep first node per external resource URL; preserve relative order."""
    seen: set[str] = set()
    out: list[Any] = []
    for n in nodes:
        key = resource_key(n)
        if key is None:
            out.append(n)
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


def extract_script_srcs(*html_parts: Any) -> list[str]:
    """Debug helper: list script/link URLs in order after flatten."""
    keys: list[str] = []
    for p in html_parts:
        if p is None:
            continue
        if isinstance(p, (list, tuple)):
            keys.extend(extract_script_srcs(*p))
            continue
        k = resource_key(p)
        if k:
            keys.append(k)
            continue
        for m in _SRC_HREF.finditer(str(p)):
            keys.append(_norm(m.group(1)))
    return keys
