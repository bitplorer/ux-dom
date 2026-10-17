# Copyright (c) 2026 ux-dom
"""
Optional **ux-channel** bridge for the ux-dom UI kit.

Does **not** import ux_channel at module import time. Call helpers when channel
is installed; pure UI components work without it.

Patterns
--------
1. **Stamp region** — attach ``data-channel-id`` to any ux-dom tree for morph targets.
2. **LiveButton** — Button that carries signed action attrs when a registry/host
   is available (via ``ux_channel.render.html.ControlAttrs``).
3. **to_fragment** — coerce ux-dom nodes to HTML strings channel morph expects.
4. **public_form** — progressive form: Channel Intent when peer present, HTML POST
   when Channel is absent. No second protocol.

::

    from ux_dom.ui import Button, Card
    from ux_dom.ui.channel_bridge import stamp_region, channel_available

    card = stamp_region(Card(CardContent("Hi")), uid="Welcome:card")
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

__all__ = [
    "channel_available",
    "stamp_region",
    "action_button_attrs",
    "to_fragment",
    "live_button",
    "public_form",
]


def channel_available() -> bool:
    try:
        import ux_channel  # noqa: F401

        return True
    except ImportError:
        return False


def to_fragment(node: Any) -> str:
    """Coerce a ux-dom node, ``__html__`` object or HTML string to an HTML string.

    A plain ``str`` is returned as-is: callers hand it HTML they already built.
    """
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if hasattr(node, "__html__"):
        return str(node.__html__())
    return str(node)  # ux-dom tags serialize on str()


def stamp_region(node: Any, *, uid: str, **data_attrs: str) -> Any:
    """Wrap *node* in a ``div`` carrying ``data-channel-id`` for channel morph."""
    from ux_dom.dom import div

    attrs = {"data-channel-id": uid}
    for k, v in data_attrs.items():
        key = k if k.startswith("data-") else f"data-{k.replace('_', '-')}"
        attrs[key] = v
    return div(node, **attrs)


def action_button_attrs(
    action: str,
    *,
    host: Any = None,
    trust: Mapping[str, Any] | None = None,
    target: str | None = None,
) -> dict[str, str]:
    """
    Return HTML attrs (raw values; the renderer escapes them) for a channel action.

    With ux-channel installed this is ``ControlAttrs(...).as_dict()``: a bare
    *target* uid becomes its region selector, and when *host* can ``mint``
    (an ActionRegistry) the attrs carry a signed ``data-channel-cap`` bound to
    *trust*. Without ux-channel it returns a ``data-channel-action`` stub so
    markup still renders in demos.
    """
    if not channel_available():
        out = {"data-channel-action": action}
        if target:
            out["data-channel-target"] = target
        return out

    from ux_channel.components.primitive import uid_sel
    from ux_channel.render.html import ControlAttrs

    if target and not target.startswith(("[", "#", ".")):
        target = uid_sel(target)
    cap = host.mint(action, dict(trust or {})) if hasattr(host, "mint") else None
    return ControlAttrs(action=action, trust=trust, cap=cap, target=target).as_dict()


def live_button(
    *children: Any,
    action: str,
    host: Any = None,
    trust: Mapping[str, Any] | None = None,
    target: str | None = None,
    variant: str = "default",
    size: str = "md",
    **attrs: Any,
):
    """ux-dom ``Button`` with channel action attrs merged in."""
    from ux_dom.ui.button import Button

    ch_attrs = action_button_attrs(action, host=host, trust=trust, target=target)
    merged = {**ch_attrs, **attrs}
    return Button(*children, variant=variant, size=size, **merged)


def public_form(
    *children: Any,
    action: str,
    href: str | None = None,
    method: str = "post",
    target: str | None = None,
    className: str = "",
    **attrs: Any,
):
    """
    Progressive form for a public Action.

    Always a valid HTML ``<form method=post>``. When Channel is present the
    same form also carries signed action attrs. No second protocol.
    """
    from ux_dom.dom import form
    from ux_dom.ui.tokens import cn

    form_action = href or f"/actions/{action}"
    extra = action_button_attrs(action, target=target)
    extra["data-progressive"] = "form"
    merged = {**extra, **attrs}
    return form(
        *children,
        action=form_action,
        method=method,
        className=cn(className) if className else None,
        **merged,
    )
