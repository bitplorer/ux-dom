# Copyright (c) 2026 ux-dom
"""ToastHost — morph target for notices. Server list is authority."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ux_dom import Component
from ux_dom.dom import div, li, ol, p, span
from ux_dom.ui.tokens import cn, status

__all__ = ["ToastHost", "ToastItem"]

_LEVELS = {
    "info": status["neutral"],
    "success": status["success"],
    "warning": status["warning"],
    "error": status["danger"],
    "destructive": status["danger"],
}


class ToastItem(Component):
    def render(
        self,
        text: str = "",
        *,
        level: str = "info",
        className: str = "",
        **attrs: Any,
    ):
        return li(
            p(text, className="text-sm"),
            className=cn(
                "rounded-lg border px-3 py-2 shadow-sm",
                _LEVELS.get(level, _LEVELS["info"]),
                className,
            ),
            **{"data-level": level},
            **attrs,
        )


class ToastHost(Component):
    """Morph-safe notices region. Items from Host Ops (ux-behavior ``notify``)."""

    def render(
        self,
        items: Sequence[Mapping[str, Any] | str] = (),
        *,
        label: str = "Notifications",
        empty: Any = None,
        className: str = "",
        **attrs: Any,
    ):
        kids: list[Any] = []
        rows = list(items)
        if not rows:
            kids.append(empty if empty is not None else span("No notices", className="sr-only"))
        for raw in rows:
            if isinstance(raw, str):
                kids.append(ToastItem(raw, level="info"))
            else:
                kids.append(
                    ToastItem(
                        str(raw.get("text") or raw.get("message") or ""),
                        level=str(raw.get("level") or "info"),
                    )
                )

        kwargs = dict(attrs)
        kwargs.setdefault("id", "notices")
        kwargs.setdefault("data-channel-id", "notices")
        return div(
            ol(*kids, className="flex flex-col gap-2"),
            role="status",
            **{"aria-live": "polite", "aria-label": label, "data-toast-host": "1"},
            className=cn("pointer-events-auto w-full max-w-sm", className),
            **kwargs,
        )
