"""Reloader internal: _models. Dev hot-reload support; not a production public API."""
from typing import NamedTuple, Sequence

from ._types import ReloadFunc


class WatchPath(NamedTuple):
    path: str
    on_reload: Sequence[ReloadFunc] = ()
