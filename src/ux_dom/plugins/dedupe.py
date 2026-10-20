# Copyright (c) 2026 ux-dom
"""Deduplicate script/link tags by src/href — prevent double injection."""

from __future__ import annotations

import re
from typing import Any, Iterable, List

from ux_dom.dom.src.dom_tag import dom_tag

# Match src= or href= in rendered HTML (attribute order varies)
_SRC_HREF = re.compile(r"""(?i)\b(?:src|href)\s*=\s*["']([^"']+)["']""")
# Raw HTML string that is itself a script/link tag (not a wrapper around one)
_OPEN_TAG = re.compile(r"""(?is)^\s*<(script|link)\b([^>]*)>""")
# Whole attribute names only: data-src / data-href / data-rel do not count
_ATTR = re.compile(r"""(?i)(?<![\w-])(src|href|rel)\s*=\s*["']([^"']*)["']""")


def _resource(node: Any) -> tuple[str, str, str] | None:
    """``(tag, rel, url)`` when *node* is itself a ``script[src]`` / ``link[href]``."""
    if node is None:
        return None
    attrs = getattr(node, "attributes", None) or getattr(node, "attrs", None)
    if isinstance(attrs, dict):
        if isinstance(node, dom_tag):
            tag = str(node._tagname()).lower()
        else:
            tag = str(getattr(node, "tagname", None) or type(node).__name__).lower()
        if tag not in ("script", "link"):
            return None  # wrappers and other tags pass through
        url = attrs.get("src" if tag == "script" else "href")
        rel = attrs.get("rel") or ""
    else:
        # Raw strings / HtmlFragment: only when the string starts with the tag
        m = _OPEN_TAG.match(str(node))
        if not m:
            return None
        tag = m.group(1).lower()
        found: dict[str, str] = {}
        for name, value in _ATTR.findall(m.group(2)):
            found.setdefault(name.lower(), value)
        url = found.get("src" if tag == "script" else "href")
        rel = found.get("rel", "")
    if not url:
        return None  # inline scripts are never deduped against each other
    # rel is a token set: "preload stylesheet" == "stylesheet preload"
    rel_key = " ".join(sorted(set(str(rel).lower().split())))
    return tag, rel_key, _norm(str(url))


def resource_key(node: Any) -> str | None:
    """
    Stable key for a DOM node if it loads an external resource.

    Returns normalized URL string, or None if node is not a script/link resource
    (inline scripts, plain divs, etc. are never deduped against each other).
    """
    res = _resource(node)
    return res[2] if res else None


def _norm(url: str) -> str:
    u = url.strip()
    # ignore fragment-only differences
    if "#" in u:
        u = u.split("#", 1)[0]
    return u


def dedupe_dom_nodes(nodes: Iterable[Any]) -> List[Any]:
    """Keep first node per (tag, rel, url) resource; preserve relative order."""
    seen: set[tuple[str, str, str]] = set()
    out: list[Any] = []
    for n in nodes:
        key = _resource(n)
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
