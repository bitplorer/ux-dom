# Copyright (c) 2026 ux-dom
"""Low-level hub → head/body tag lists.

Prefer ``Document(...).use(...)`` in app code (SSoT).
``shell_fragments`` / ``runtime_tags`` are low-level list helpers only.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from ux_dom.plugins.hub import PluginHub, get_hub


def runtime_tags(
    hub: Optional[PluginHub] = None,
    *extra_head: Any,
    extra_body: Sequence[Any] = (),
    dedupe: bool = True,
) -> tuple[list[Any], list[Any]]:
    """
    Return ``(head_tags, body_tags)`` from the App hub.

    Same as ``shell_fragments`` — preferred name for clarity.
    """
    return shell_fragments(hub, *extra_head, extra_body=extra_body, dedupe=dedupe)


def shell_fragments(
    hub: Optional[PluginHub] = None,
    *extra_head: Any,
    extra_body: Sequence[Any] = (),
    dedupe: bool = True,
) -> tuple[list[Any], list[Any]]:
    """Head/body nodes from hub contributions (+ optional extras)."""
    h = hub or get_hub()
    head, body = h.shell_fragments(dedupe=dedupe)
    if extra_head:
        head = list(head) + list(extra_head)
    if extra_body:
        body = list(body) + list(extra_body)
    if dedupe:
        from ux_dom.plugins.dedupe import dedupe_dom_nodes

        head = dedupe_dom_nodes(head)
        body = dedupe_dom_nodes(body)
    try:
        from ux_dom.plugins.csp import get_nonce, stamp_nonce

        if get_nonce():
            head = stamp_nonce(head)
            body = stamp_nonce(body)
    except Exception:
        pass
    return head, body
