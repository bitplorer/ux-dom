"""ChannelControl — stack-native control plane (semantic data-ux-* attrs).

Does not import ux_channel. Live transport is attached separately via
``UxChannelRuntime`` / compose ``use_channel``. This plugin only owns
tag attrs so product code stays host-agnostic: ``control("shop.add")``.

HTMX remains a separate opt-in ControlPlugin (``HtmxControl``).
"""
from __future__ import annotations

from typing import Any, Sequence


class ChannelControl:
    """Semantic control plane: data-ux-action / data-ux-arg-*.

    Preferred Day-1 default when live channel is available (or offline
    progressive enhancers that understand the same attrs).
    """

    plugin_kind = "control"
    name = "channel"

    def artifacts(self):
        return ()

    def document_head(self) -> Sequence[Any]:
        return ()

    def document_body(self) -> Sequence[Any]:
        return ()

    def wire(self, action: Any = None, **kwargs: Any) -> dict[str, Any]:
        """Return kwargs safe to splat onto a tag (data-ux-*)."""
        if action is None:
            return {}
        if not isinstance(action, str):
            action = getattr(action, "action", None) or getattr(action, "__name__", str(action))
        attrs: dict[str, Any] = {"data-ux-action": str(action)}
        for k, v in kwargs.items():
            if v is None:
                continue
            attrs[f"data-ux-arg-{k}"] = str(v)
        return attrs

    def partial_policy(self, request: Any) -> str:
        return "partial"

    def mount(self, app: Any, **kwargs: Any) -> None:
        return None


__all__ = ["ChannelControl"]
