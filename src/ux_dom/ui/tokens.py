# Copyright (c) 2026 ux-dom
"""Design tokens and class-merge helpers (shadcn-like, Tailwind utility based)."""

from __future__ import annotations

from typing import Iterable, Optional

__all__ = ["cn", "variants", "focus_ring", "radius"]

# Shared radius / focus (match Tailwind defaults used in create-app)
radius = {
    "sm": "rounded-md",
    "md": "rounded-lg",
    "lg": "rounded-xl",
    "full": "rounded-full",
}

focus_ring = (
    "focus-visible:outline-none focus-visible:ring-2 "
    "focus-visible:ring-slate-400 focus-visible:ring-offset-2"
)


def cn(*parts: Optional[str | Iterable[str] | bool]) -> str:
    """Merge class fragments (truthy strings only)."""
    out: list[str] = []
    for p in parts:
        if not p or p is True:
            continue
        if isinstance(p, str):
            out.append(p.strip())
        else:
            for x in p:
                if x and isinstance(x, str):
                    out.append(x.strip())
    # collapse whitespace
    return " ".join(" ".join(out).split())


def variants(table: dict[str, dict[str, str]], **chosen: str) -> str:
    """Pick classes from a variant table.

    ::

        variants(
            {"size": {"sm": "h-8", "md": "h-10"}, "variant": {"default": "..."}},
            size="sm",
            variant="default",
        )
    """
    chunks: list[str] = []
    for axis, value in chosen.items():
        axis_map = table.get(axis) or {}
        if value in axis_map:
            chunks.append(axis_map[value])
        elif "default" in axis_map and value is None:
            chunks.append(axis_map["default"])
    return cn(*chunks)
