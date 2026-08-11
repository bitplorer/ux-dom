# Copyright (c) 2023 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""HTMX-oriented helpers. Prefer Htmx / HtmxControl from runtime/plugins."""
import typing

from ux_dom.htmx.middleware import HtmxMiddleware
from ux_dom.web_io import HtmxEvents

__all__ = ["Htmx", "HtmxMiddleware"]


class Htmx(HtmxEvents):
    """Decorate Component handlers and mount them on an API router.

    Breaking (0.5): routes default under ``prefix`` (default ``""`` for
    Prefer an explicit namespace (``/{name}`` is allowed when unset)::

        htmx = Htmx(api=api, prefix="/actions")

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

    def get(self, event):
        wrapper = super(Htmx, self).get(event)
        return self.api.get(self._path(self._event_name(event)))(wrapper)

    def post(self, event):
        wrapper = super(Htmx, self).post(event)
        return self.api.post(self._path(self._event_name(event)))(wrapper)

    def put(self, event):
        wrapper = super(Htmx, self).put(event)
        return self.api.put(self._path(self._event_name(event)))(wrapper)

    def patch(self, event):
        wrapper = super(Htmx, self).patch(event)
        return self.api.patch(self._path(self._event_name(event)))(wrapper)

    def delete(self, event):
        wrapper = super(Htmx, self).delete(event)
        return self.api.delete(self._path(self._event_name(event)))(wrapper)
