"""Removed from the product path.

Product host strategy lives on **ux-compose** (`build(host=)` / FastAPI()
at the composition root). This class remains importable so leftover
callers fail closed with a teaching error instead of standing up a
second FastAPI factory on the render library.
"""
from __future__ import annotations

from typing import Any, Optional, Sequence


_TEACH = (
    "FastAPIHost is not a ux-dom render API. "
    "Product host is ux_compose.build(host=) / FastAPI() + App.mount. "
    "Scaffold: uxcompose create-app / uxcompose serve. "
    "Leftover plugins.App.build() takes asgi=FastAPI() — it does not invent a host."
)


class ProductHostMoved(RuntimeError):
    """Raised when a caller constructs product FastAPI from ux-dom."""

    def __init__(self, message: str = _TEACH):
        super().__init__(message)


class FastAPIHost:
    """Fail-closed. Product host is ``ux_compose.build(host=)``."""

    plugin_kind = "host"
    name = "fastapi"

    def __init__(
        self,
        title: str = "ux-dom",
        debug: Optional[bool] = None,
        default_response_class: Any = None,
        route_class: Any = None,
        static_mounts: Optional[Sequence[tuple[str, Any]]] = None,
        lifespan_hooks: Optional[Sequence[Any]] = None,
    ):
        raise ProductHostMoved()

    def mount(self, app: Any = None, settings: Any = None, **kwargs: Any) -> Any:
        raise ProductHostMoved()


__all__ = ["FastAPIHost", "ProductHostMoved"]
