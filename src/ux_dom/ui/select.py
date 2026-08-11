# Copyright (c) 2026 ux-dom
"""UI kit component: select.

Optional Tailwind-styled building block. List with `uxdom ui`; copy with `uxdom add ui Select` when applicable. Not required for core ux-dom apps.
"""
from __future__ import annotations

from typing import Any, Sequence

from ux_dom import Component
from ux_dom.dom import option, select
from ux_dom.ui.tokens import cn, focus_ring

__all__ = ["Select"]


class Select(Component):
    def render(
        self,
        options: Sequence[tuple[str, str]] | Sequence[str] = (),
        *,
        className: str = "",
        placeholder: str | None = None,
        **attrs: Any,
    ):
        kids = []
        has_value = "value" in attrs and attrs.get("value") not in (None, "")
        if placeholder is not None:
            kw = {"value": "", "disabled": True}
            if not has_value:
                kw["selected"] = True
            kids.append(option(placeholder, **kw))
        for opt in options:
            if isinstance(opt, (list, tuple)) and len(opt) == 2:
                val, label = opt[0], opt[1]
            else:
                val = label = str(opt)
            kw = {"value": val}
            if has_value and str(attrs.get("value")) == str(val):
                kw["selected"] = True
            kids.append(option(label, **kw))
        return select(
            *kids,
            className=cn(
                "flex h-10 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm",
                focus_ring,
                className,
            ),
            **attrs,
        )
