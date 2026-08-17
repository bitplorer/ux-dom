# Copyright (c) 2026 ux-dom
"""Tabs — Channel-first selection (no Alpine by default).

Active tab comes from the server (select_region / session).
Render only the active panel + tab list with live_button / action attrs.

::

    # Action
    return select_region("tabs:main", tab)

    # Render
    Tabs(
        items=[("a", "Alpha", body_a), ("b", "Beta", body_b)],
        active=world.kv.get("ui.select.tabs.main") or "a",
        select_action="nav.tab",  # optional: stamp action attrs on tab buttons
    )
"""
from __future__ import annotations

import re
from typing import Any, Sequence

from ux_dom import Component
from ux_dom.dom import button, div
from ux_dom.ui.tokens import cn, focus_ring, surface

__all__ = ["Tabs"]

_SAFE_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def _safe_key(key: str, fallback: str) -> str:
    k = str(key)
    return k if _SAFE_KEY.match(k) else fallback


class Tabs(Component):
    """Server-driven tabs. Active key is an argument — not client state."""

    def render(
        self,
        items: Sequence[tuple[str, str, Any]] = (),
        *,
        active: str | None = None,
        default: str | None = None,
        select_action: str | None = None,
        className: str = "",
        **attrs: Any,
    ):
        if not items:
            return div(**({"className": className} if className else {}), **attrs)

        normalized: list[tuple[str, str, Any]] = []
        for i, row in enumerate(items):
            if len(row) != 3:
                raise ValueError(
                    f"Tabs items must be (key, label, body) triples, got {row!r}"
                )
            key, label, body = row
            normalized.append((_safe_key(key, f"tab{i}"), label, body))

        keyset = {k for k, _, _ in normalized}
        chosen = active if active is not None else default
        current = chosen if chosen in keyset else normalized[0][0]

        tab_btns = []
        active_body: Any = None
        for key, label, body in normalized:
            is_active = key == current
            btn_attrs: dict[str, Any] = {"type": "button"}
            if select_action:
                btn_attrs["data-channel-action"] = select_action
                btn_attrs["data-args"] = f'{{"tab":"{key}"}}'
            tab_btns.append(
                button(
                    label,
                    className=cn(
                        "inline-flex min-h-9 items-center justify-center whitespace-nowrap rounded-md",
                        "px-3 py-1.5 text-sm font-medium transition-all",
                        focus_ring,
                        "bg-stone-800 text-stone-100 shadow-sm"
                        if is_active
                        else "text-stone-400 hover:text-stone-200",
                    ),
                    **{"aria-selected": "true" if is_active else "false"},
                    **{"data-tab": key},
                    **btn_attrs,
                )
            )
            if is_active:
                active_body = body

        return div(
            div(
                *tab_btns,
                role="tablist",
                className=cn(
                    "inline-flex items-center rounded-lg p-1",
                    surface["l1"],
                ),
            ),
            div(
                active_body,
                role="tabpanel",
                className="mt-4 text-sm text-stone-200",
            ),
            className=cn(className) if className else None,
            **attrs,
        )
