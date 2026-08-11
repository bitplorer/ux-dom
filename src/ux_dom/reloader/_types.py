"""Reloader internal: _types. Dev hot-reload support; not a production public API."""
from typing import Awaitable, Callable

ReloadFunc = Callable[[], Awaitable[None]]
