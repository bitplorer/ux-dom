# Copyright (c) 2026 ux-dom
"""UI kit component: table.

Optional Tailwind-styled building block. List with `uxdom ui`; copy with `uxdom add ui Table` when applicable. Not required for core ux-dom apps.
"""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import caption, table, tbody, td, th, thead, tr
from ux_dom.ui.tokens import cn

__all__ = [
    "Table",
    "TableHeader",
    "TableBody",
    "TableRow",
    "TableHead",
    "TableCell",
    "TableCaption",
    "TableEmpty",
]


class Table(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return table(
            *children,
            className=cn("w-full caption-bottom text-sm", className),
            **attrs,
        )


class TableHeader(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return thead(*children, className=cn("[&_tr]:border-b", className), **attrs)


class TableBody(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return tbody(
            *children,
            className=cn("[&_tr:last-child]:border-0", className),
            **attrs,
        )


class TableRow(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return tr(
            *children,
            className=cn(
                "border-b border-slate-100 transition-colors hover:bg-slate-50/80",
                className,
            ),
            **attrs,
        )


class TableHead(Component):
    def render(
        self,
        *children: Any,
        className: str = "",
        sorted: str | None = None,
        **attrs: Any,
    ):
        extra = ""
        aria: dict[str, Any] = {}
        if sorted in {"asc", "desc"}:
            extra = "text-slate-900"
            aria["aria-sort"] = "ascending" if sorted == "asc" else "descending"
        return th(
            *children,
            className=cn(
                "h-12 px-4 text-left align-middle font-medium text-slate-500",
                extra,
                className,
            ),
            **aria,
            **attrs,
        )


class TableCell(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return td(
            *children,
            className=cn("p-4 align-middle", className),
            **attrs,
        )


class TableCaption(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return caption(
            *children,
            className=cn("mt-4 text-sm text-slate-500", className),
            **attrs,
        )


class TableEmpty(Component):
    """Empty-state row. Span the full table width."""

    def render(
        self,
        *children: Any,
        col_span: int = 1,
        className: str = "",
        **attrs: Any,
    ):
        body = children or ("No rows",)
        return tr(
            td(
                *body,
                colSpan=col_span,
                className=cn(
                    "p-8 text-center text-sm text-slate-500",
                    className,
                ),
                **attrs,
            )
        )
