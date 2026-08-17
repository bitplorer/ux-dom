# Copyright (c) 2026 ux-dom
"""Table — operational dark surface hierarchy."""
from __future__ import annotations

from typing import Any

from ux_dom import Component
from ux_dom.dom import caption, table, tbody, td, th, thead, tr
from ux_dom.ui.tokens import cn, ink, type_scale

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
            className=cn("w-full caption-bottom text-sm text-stone-100", className),
            **attrs,
        )


class TableHeader(Component):
    def render(self, *children: Any, className: str = "", **attrs: Any):
        return thead(
            *children,
            className=cn("[&_tr]:border-b [&_tr]:border-stone-800", className),
            **attrs,
        )


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
                "border-b border-stone-800 transition-colors hover:bg-stone-800/50",
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
        aria: dict[str, Any] = {}
        extra = ""
        if sorted in {"asc", "desc"}:
            extra = "text-stone-100"
            aria["aria-sort"] = "ascending" if sorted == "asc" else "descending"
        return th(
            *children,
            className=cn(
                "h-11 px-4 text-left align-middle font-medium",
                ink["muted"],
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
            className=cn("mt-4", type_scale["caption"], className),
            **attrs,
        )


class TableEmpty(Component):
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
                    "p-8 text-center",
                    type_scale["caption"],
                    className,
                ),
                **attrs,
            )
        )
