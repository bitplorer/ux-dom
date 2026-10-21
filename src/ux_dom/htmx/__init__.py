# Copyright (c) 2023 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""HTMX route decorator and middleware. The document runtime is ``ux_dom.Htmx``."""
import typing

from ux_dom.htmx.middleware import HtmxMiddleware
from ux_dom.web_io import HtmxEvents

__all__ = ["HtmxMiddleware", "HtmxRoutes"]


class HtmxRoutes(HtmxEvents):
    """Decorate Component handlers and mount them on an API router.

    Routes mount at ``{prefix}/{name}``; with the default ``prefix=""`` they
    mount at ``/{name}``. Prefer an explicit namespace::

        htmx = HtmxRoutes(api=api, prefix="/actions")

        @htmx.get
        def counter(): ...
        # → GET /actions/counter
    """

    def __init__(self, api: typing.Any, prefix: str = ""):
        self.api = api
        self.prefix = (prefix or "").rstrip("/")
        super().__init__()

    def _path(self, name: str) -> str:
        if self.prefix:
            return f"{self.prefix}/{name}"
        return f"/{name}"

    def _event_name(self, event) -> str:
        """Stable route name from the decorated callable (not list tail)."""
        if isinstance(event, str):
            return event
        return getattr(event, "__name__", str(event))

    def _route(self, verb: str, event):
        registered = getattr(super(HtmxRoutes, self), verb)(event)
        route = getattr(self.api, verb)(self._path(self._event_name(event)))
        if isinstance(event, str):
            # ``@htmx.get("name")``: route the decorated function, not the decorator.
            return lambda fn: route(registered(fn))
        return route(registered)

    def get(self, event):
        return self._route("get", event)

    def post(self, event):
        return self._route("post", event)

    def put(self, event):
        return self._route("put", event)

    def patch(self, event):
        return self._route("patch", event)

    def delete(self, event):
        return self._route("delete", event)
