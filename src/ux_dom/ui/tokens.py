# Copyright (c) 2026 ux-dom
"""Design tokens and class-merge helpers (operational craft, Tailwind utility based).

Elevated for Host desks and product surfaces:
- L0–L3 surface language (page → card → elevated → popover)
- Operational type scale
- 44px minimum targets (min-h-11)
- Density + overlay grammar
- Pure Tailwind; no second design system

Public contract preserved: cn, variants, focus_ring, radius.
"""

from __future__ import annotations

from typing import Iterable, Optional

__all__ = [
    "cn",
    "variants",
    "focus_ring",
    "radius",
    "surface",
    "ink",
    "type_scale",
    "target",
    "density",
    "overlay",
    "color",
    "field_classes",
]

# ── Shared radius / focus ────────────────────────────────────────────────────
radius = {
    "sm": "rounded-md",
    "md": "rounded-lg",
    "lg": "rounded-xl",
    "full": "rounded-full",
}

# Stronger, more operational focus (works on dark and light paper)
focus_ring = (
    "focus-visible:outline-none focus-visible:ring-2 "
    "focus-visible:ring-stone-400/80 focus-visible:ring-offset-2 "
    "focus-visible:ring-offset-transparent"
)

# ── Surface levels (L0 page → L3 popover) ────────────────────────────────────
# Designed so Host can drop local brown hacks and inherit hierarchy.
surface = {
    "l0": "bg-stone-950 text-stone-100",          # page / site-frame
    "l1": "bg-stone-900/90 text-stone-100 border border-stone-800/80",  # card / panel
    "l2": "bg-stone-900 text-stone-50 border border-stone-700/60 shadow-md",  # elevated / modal body
    "l3": "bg-stone-800 text-stone-50 border border-stone-600/50 shadow-md",  # popover / command
    # Light fallbacks (ownable when product needs light)
    "l0_light": "bg-stone-50 text-stone-950",
    "l1_light": "bg-white text-stone-950 border border-stone-200 shadow-sm",
    "l2_light": "bg-white text-stone-950 border border-stone-200 shadow-md",
    "l3_light": "bg-white text-stone-950 border border-stone-200 shadow-lg",
}

# Semantic ink
ink = {
    "primary": "text-stone-100",
    "muted": "text-stone-400",
    "faint": "text-stone-500",
    "accent": "text-emerald-400",
    "danger": "text-red-400",
    "primary_light": "text-stone-950",
    "muted_light": "text-stone-500",
}

# Operational type scale
type_scale = {
    "display": "text-2xl font-semibold tracking-tight",
    "title": "text-lg font-semibold tracking-tight",
    "subtitle": "text-sm font-medium text-stone-300",
    "body": "text-sm leading-relaxed",
    "caption": "text-xs text-stone-400",
    "label": "text-xs font-medium uppercase tracking-wide text-stone-400",
}

# Touch / click targets (44px floor for primary actions)
target = {
    "sm": "min-h-9 h-9 px-3 text-xs",
    "md": "min-h-11 h-11 px-4 text-sm",   # default — 44px
    "lg": "min-h-12 h-12 px-6 text-base",
    "icon": "min-h-11 h-11 w-11",
}

# Density rhythm
density = {
    "compact": "space-y-2 gap-2",
    "default": "space-y-3 gap-3",
    "relaxed": "space-y-4 gap-4",
    "section": "space-y-6",
}

# Overlay grammar (modals, sheets, command, popovers)
overlay = {
    "backdrop": "fixed inset-0 z-40 bg-black/60 backdrop-blur-[2px]",
    "modal": "fixed inset-0 z-50 flex items-center justify-center p-4",
    "sheet": "fixed inset-x-0 bottom-0 z-50 max-h-[85vh] rounded-t-2xl",
    "command": "fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2",
    "popover": "absolute z-50 min-w-[12rem] rounded-xl",
}

# Semantic color roles (Material-inspired, Tailwind utility mapped)
# Use these for brand/theme overrides without fighting surface levels.
color = {
    "background": "bg-stone-950",
    "foreground": "text-stone-100",
    "primary": "bg-stone-100 text-stone-950",
    "primary_fg": "text-stone-950",
    "secondary": "bg-stone-800 text-stone-100",
    "muted": "bg-stone-900 text-stone-400",
    "destructive": "bg-red-600 text-white",
    "accent": "bg-emerald-600 text-white",
    "border": "border-stone-700",
    "input": "border-stone-700 bg-stone-950/60",
    "ring": "ring-stone-400/80",
    "card": "bg-stone-900/90 border-stone-800/80",
    "popover": "bg-stone-800 border-stone-600/50",
    # light
    "background_light": "bg-stone-50",
    "foreground_light": "text-stone-950",
    "primary_light": "bg-stone-900 text-stone-50",
    "border_light": "border-stone-200",
    "card_light": "bg-white border-stone-200",
}


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

def field_classes(*, className: str = "", invalid: bool = False) -> str:
    """Shared control chrome for Input / Select / DatePicker alignment."""
    return cn(
        "flex min-h-11 h-11 w-full rounded-lg border bg-stone-950/60 px-3 py-2 text-sm text-stone-100",
        "placeholder:text-stone-500 disabled:cursor-not-allowed disabled:opacity-50",
        focus_ring,
        "border-red-500/80" if invalid else "border-stone-700",
        className,
    )

