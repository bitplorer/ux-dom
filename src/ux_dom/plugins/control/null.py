"""NullControl — no-op control plugin for tests and minimal shells."""
from __future__ import annotations

from typing import Any, Sequence


class NullControl:
    """No-op control plane (tests / static sites)."""

    plugin_kind = "control"
    name = "null"

    def artifacts(self):
        return ()

    def document_head(self) -> Sequence[Any]:
        return ()

    def document_body(self) -> Sequence[Any]:
        return ()

    def wire(self, action: Any = None, **kwargs: Any) -> dict[str, Any]:
        return {}

    def partial_policy(self, request: Any) -> str:
        return "full"

    def mount(self, app: Any, **kwargs: Any) -> None:
        return None
