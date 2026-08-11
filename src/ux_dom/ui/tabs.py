# Copyright (c) 2026 ux-dom
"""Tabs — Alpine.js powered (x-data). Falls back to first panel only without Alpine."""

from __future__ import annotations

import re
from typing import Any, Sequence

from ux_dom import Component
from ux_dom.dom import button, div
from ux_dom.ui.tokens import cn, focus_ring

__all__ = ["Tabs"]

_SAFE_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def _safe_key(key: str, fallback: str) -> str:
    k = str(key)
    if _SAFE_KEY.match(k):
        return k
    # deterministic safe token
    return fallback


class Tabs(Component):
    """
    ::

        Tabs(
            items=[("a", "Alpha", div("A body")), ("b", "Beta", div("B body"))],
            default="a",
        )

    Keys must be simple identifiers (``[A-Za-z_][A-Za-z0-9_-]*``). Unsafe keys
    are rewritten to ``tab0``, ``tab1``, … so Alpine bindings never break.
    """

    def render(
        self,
        items: Sequence[tuple[str, str, Any]] = (),
        *,
        default: str | None = None,
        className: str = "",
        **attrs: Any,
    ):
        if not items:
            return div(**({} if not className else {"className": className}), **attrs)

        normalized: list[tuple[str, str, Any]] = []
        for i, row in enumerate(items):
            if len(row) != 3:
                raise ValueError(
                    f"Tabs items must be (key, label, body) triples, got {row!r}"
                )
            key, label, body = row
            normalized.append((_safe_key(key, f"tab{i}"), label, body))

        # Map default through same sanitizer when possible
        keyset = {k for k, _, _ in normalized}
        if (
            default is not None
            and _SAFE_KEY.match(str(default))
            and str(default) in keyset
        ):
            first = str(default)
        else:
            first = normalized[0][0]

        tab_btns = []
        panels = []
        for key, label, body in normalized:
            tab_btns.append(
                button(
                    label,
                    type="button",
                    **{
                        "@click": f"tab = '{key}'",
                        ":class": (
                            f"tab === '{key}' ? 'bg-white shadow-sm' : 'text-slate-500'"
                        ),
                    },
                    className=cn(
                        "inline-flex items-center justify-center whitespace-nowrap rounded-md",
                        "px-3 py-1.5 text-sm font-medium transition-all",
                        focus_ring,
                    ),
                )
            )
            panels.append(
                div(
                    body,
                    **{"x-show": f"tab === '{key}'"},
                    className="mt-4 text-sm",
                )
            )
        return div(
            div(
                *tab_btns,
                className="inline-flex h-10 items-center rounded-lg bg-slate-100 p-1",
            ),
            *panels,
            **{"x-data": f"{{ tab: '{first}' }}"},
            className=cn(className) if className else None,
            **attrs,
        )
