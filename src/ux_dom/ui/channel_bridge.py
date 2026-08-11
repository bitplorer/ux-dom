# Copyright (c) 2026 ux-dom
"""
Optional **ux-channel** bridge for the ux-dom UI kit.

Does **not** import ux_channel at module import time. Call helpers when channel
is installed; pure UI components work without it.

Patterns
--------
1. **Stamp region** — attach ``data-channel-id`` to any ux-dom tree for morph targets.
2. **LiveButton** — Button that carries signed action attrs when a registry/host
   is available (via ux_channel.components.primitive.region_button / action_attrs).
3. **to_fragment** — coerce ux-dom nodes to HTML strings channel morph expects.

::

    from ux_dom.ui import Button, Card
    from ux_dom.ui.channel_bridge import stamp_region, channel_available

    card = stamp_region(Card(CardContent("Hi")), uid="Welcome:card")
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

__all__ = [
    "channel_available",
    "stamp_region",
    "action_button_attrs",
    "to_fragment",
    "live_button",
]


def channel_available() -> bool:
    try:
        import ux_channel  # noqa: F401

        return True
    except ImportError:
        return False


def to_fragment(node: Any) -> str:
    """Coerce ux-dom / str / ``__html__`` to an HTML string."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if hasattr(node, "__html__"):
        return str(node.__html__())  # type: ignore[misc]
    # ux-dom render path
    if hasattr(node, "__render__"):
        try:
            return str(node.__render__())
        except Exception:
            pass
    return str(node)


def stamp_region(node: Any, *, uid: str, **data_attrs: str) -> Any:
    """
    Ensure the root element exposes ``data-channel-id`` for channel morph.

    Mutates kwargs on the outer tag when possible; otherwise wraps in a div.
    """
    from ux_dom.dom import div

    attrs = {f"data-channel-id": uid}
    for k, v in data_attrs.items():
        key = k if k.startswith("data-") else f"data-{k.replace('_', '-')}"
        attrs[key] = v

    # Prefer wrapping — safe for any Component tree
    return div(node, **attrs)


def action_button_attrs(
    action: str,
    *,
    host: Any = None,
    trust: Optional[Mapping[str, Any]] = None,
    target: Optional[str] = None,
) -> dict[str, str]:
    """
    Return HTML attrs for a channel action control.

    Without ux-channel, returns a ``data-channel-action`` stub (non-functional) so
    markup still renders in demos.
    """
    if not channel_available():
        out = {"data-channel-action": action}
        if target:
            out["data-channel-target"] = target
        return out
    try:
        from ux_channel.components.primitive import region_attrs

        # region_attrs returns a string of attrs — parse lightly is hard;
        # prefer action_attrs if present
        try:
            from ux_channel.html import action_attrs

            s = action_attrs(action, trust=trust, target=target)
            return _parse_attr_string(s)
        except Exception:
            s = region_attrs(action, trust=trust, target=target)
            return _parse_attr_string(s)
    except Exception:
        return {"data-channel-action": action}


def _parse_attr_string(s: str) -> dict[str, str]:
    """Best-effort parse ``k="v"`` pairs from channel helpers."""
    import re

    out: dict[str, str] = {}
    for m in re.finditer(r'([^\s=]+)="([^"]*)"', s or ""):
        out[m.group(1)] = m.group(2)
    return out


def live_button(
    *children: Any,
    action: str,
    host: Any = None,
    trust: Optional[Mapping[str, Any]] = None,
    target: Optional[str] = None,
    variant: str = "default",
    size: str = "md",
    **attrs: Any,
):
    """ux-dom ``Button`` with channel action attrs merged in."""
    from ux_dom.ui.button import Button

    ch_attrs = action_button_attrs(action, host=host, trust=trust, target=target)
    merged = {**ch_attrs, **attrs}
    return Button(*children, variant=variant, size=size, **merged)
