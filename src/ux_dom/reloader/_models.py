"""Reloader internal: _models. Dev hot-reload support; not a production public API."""
from collections.abc import Sequence
from typing import NamedTuple

from ._types import ReloadFunc


class WatchPath(NamedTuple):
    path: str
    on_reload: Sequence[ReloadFunc] = ()
