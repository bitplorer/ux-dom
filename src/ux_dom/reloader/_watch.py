"""Reloader internal: _watch. Dev hot-reload support; not a production public API."""

import asyncio
import itertools
import logging
from collections.abc import Awaitable, Callable

try:
    import watchfiles as _watchfiles  # optional dev extra
except ImportError:  # pragma: no cover
    _watchfiles = None  # type: ignore

logger = logging.getLogger(__name__)

ChangeSet = dict[str, list[str]]


def _change_labels():
    if _watchfiles is not None:
        return {
            _watchfiles.Change.added: "added",
            _watchfiles.Change.modified: "modified",
            _watchfiles.Change.deleted: "deleted",
        }
    return {}


CHANGE_EVENT_LABELS = _change_labels()


class FileWatcher:
    def __init__(
        self, path: str, on_change: Callable[[ChangeSet], Awaitable[None]]
    ) -> None:
        self._path = path
        self._on_change = on_change
        self._task: asyncio.Task | None = None

    @property
    def _should_exit(self) -> asyncio.Event:
        # Create lazily as hot reload may not run in the same thread as the one this
        # object was created in.
        if not hasattr(self, "_should_exit_obj"):
            self._should_exit_obj = asyncio.Event()
        return self._should_exit_obj

    async def _watch(self) -> None:
        if _watchfiles is None:
            raise RuntimeError(
                "ux_dom.reloader requires watchfiles; pip install watchfiles"
            )
        async for changes in _watchfiles.awatch(self._path):
            changeset: ChangeSet = {}
            for event, group in itertools.groupby(changes, key=lambda item: item[0]):
                label = CHANGE_EVENT_LABELS[event]
                changeset[label] = [path for _, path in group]
            await self._on_change(changeset)

    async def _main(self) -> None:
        tasks = [
            asyncio.create_task(self._watch()),
            asyncio.create_task(self._should_exit.wait()),
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        [task.cancel() for task in pending]
        [task.result() for task in done]

    async def startup(self) -> None:
        assert self._task is None
        self._task = asyncio.create_task(self._main())
        logger.info(f"Started watching file changes at {self._path!r}")

    async def shutdown(self) -> None:
        assert self._task is not None
        logger.info("Stopping file watching...")
        self._should_exit.set()
        await self._task
        self._task = None
