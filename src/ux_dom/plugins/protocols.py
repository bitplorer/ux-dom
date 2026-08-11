# Copyright (c) 2026 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Extension contracts for ux-dom plugins (stdlib typing only)."""

from __future__ import annotations

from typing import (
    Any,
    Callable,
    Literal,
    Optional,
    Protocol,
    Sequence,
    runtime_checkable,
)

PartialPolicy = Literal["full", "partial"]


@runtime_checkable
class HostPlugin(Protocol):
    """Mount ux-dom onto a web framework (FastAPI, Starlette, raw ASGI)."""

    name: str

    def mount(self, app: Any, *, settings: Any = None, **kwargs: Any) -> Any: ...


@runtime_checkable
class RoutingPlugin(Protocol):
    """File-based / programmatic route discovery (DirectoryRouter family)."""

    name: str

    def include(self, app: Any, **kwargs: Any) -> Any:
        """Attach routes (e.g. DirectoryRouter) to ``app``."""
        ...


@runtime_checkable
class ResponsePlugin(Protocol):
    """Turn Component / dom_tag into framework HTTP responses."""

    name: str

    def wrap(self, endpoint: Callable[..., Any]) -> Callable[..., Any]: ...


@runtime_checkable
class AssetsPlugin(Protocol):
    name: str

    def layout(self, base_dir: Any, **kwargs: Any) -> Any: ...


@runtime_checkable
class StylePlugin(Protocol):
    """CSS pipeline (Tailwind, Uno, none)."""

    name: str

    def stylesheet_href(self) -> str: ...

    async def build(self, *, watch: bool = False) -> Any: ...


@runtime_checkable
class HmrPlugin(Protocol):
    name: str

    def client_script(self) -> str: ...

    def asgi_route(self) -> Optional[tuple[str, Any]]: ...


@runtime_checkable
class ControlPlugin(Protocol):
    """Hypermedia control plane (HTMX, ux-channel, stack, null).

    Isolates Intent/partial policy / client scripts from core markup.
    """

    name: str

    def document_head(self) -> Sequence[Any]: ...

    def document_body(self) -> Sequence[Any]: ...

    def wire(self, action: Any = None, **kwargs: Any) -> dict[str, Any]:
        """Return kwargs safe to splat onto a tag (hx_* or data_channel_*)."""
        ...

    def partial_policy(self, request: Any) -> PartialPolicy: ...

    def mount(self, app: Any, **kwargs: Any) -> None: ...
