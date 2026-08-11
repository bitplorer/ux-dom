# Copyright (c) 2026 UX-DOM
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Per-tree locks + parallel rendering with **opt-in / opt-out** policy.

Design
------
* **Safety locks default ON** — same-tree mutation/render never tears.
* **Parallel execution defaults ON for multi-item helpers**, but falls back to
  sequential when disabled, ``max_workers=1``, or item count < threshold.
* **Usage patterns unchanged** — same call sites; policy is global / env / kwarg.
* **Independent trees stay parallel** when policy allows; no process-global lock.

Env (optional)
--------------
* ``UX_DOM_PARALLEL`` — ``1``/``0``/``true``/``false`` (default: enabled)
* ``UX_DOM_MAX_WORKERS`` — int (default: auto CPU bound)
* ``UX_DOM_PARALLEL_MIN_ITEMS`` — int (default: 2)
* ``UX_DOM_TREE_LOCKS`` — ``1``/``0`` (default: enabled; only disable in tests)
"""

from __future__ import annotations

import asyncio
import os
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, replace
from typing import Any, Callable, Iterable, Iterator, Optional, Sequence, TypeVar

__all__ = [
    "ConcurrencySettings",
    "configure_concurrency",
    "get_concurrency_settings",
    "reset_concurrency_settings",
    "root_of",
    "tree_lock_for",
    "multi_tree_lock",
    "locked_tree",
    "default_workers",
    "render_parallel",
    "build_parallel",
    "map_parallel",
    "render_async_gather",
    "should_parallelize",
]

T = TypeVar("T")
R = TypeVar("R")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: Optional[int]) -> Optional[int]:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class ConcurrencySettings:
    """Process-level concurrency policy for ux-dom.

    Defaults are **sensible production** values; override via
    :func:`configure_concurrency` or environment variables.
    """

    parallel_enabled: bool = True
    max_workers: Optional[int] = None  # None → auto
    min_items_for_parallel: int = 2
    tree_locks_enabled: bool = True

    @classmethod
    def from_env(cls) -> "ConcurrencySettings":
        return cls(
            parallel_enabled=_env_bool("UX_DOM_PARALLEL", True),
            max_workers=_env_int("UX_DOM_MAX_WORKERS", None),
            min_items_for_parallel=max(1, _env_int("UX_DOM_PARALLEL_MIN_ITEMS", 2) or 2),
            tree_locks_enabled=_env_bool("UX_DOM_TREE_LOCKS", True),
        )


_SETTINGS = ConcurrencySettings.from_env()
_SETTINGS_GUARD = threading.RLock()

_LOCKS: dict[int, threading.RLock] = {}
_LOCKS_GUARD = threading.RLock()
_POOL: Optional[ThreadPoolExecutor] = None
_POOL_GUARD = threading.Lock()
_POOL_WORKERS: int = 0


def get_concurrency_settings() -> ConcurrencySettings:
    with _SETTINGS_GUARD:
        return _SETTINGS


def configure_concurrency(
    *,
    parallel_enabled: Optional[bool] = None,
    max_workers: Optional[int] = None,
    min_items_for_parallel: Optional[int] = None,
    tree_locks_enabled: Optional[bool] = None,
    reset_pool: bool = True,
) -> ConcurrencySettings:
    """Opt-in / opt-out parallel behaviour without changing call sites.

    Pass only fields you want to change. Returns the effective settings.
    """
    global _SETTINGS, _POOL, _POOL_WORKERS
    with _SETTINGS_GUARD:
        cur = _SETTINGS
        _SETTINGS = replace(
            cur,
            parallel_enabled=cur.parallel_enabled
            if parallel_enabled is None
            else bool(parallel_enabled),
            max_workers=cur.max_workers if max_workers is None else max_workers,
            min_items_for_parallel=cur.min_items_for_parallel
            if min_items_for_parallel is None
            else max(1, int(min_items_for_parallel)),
            tree_locks_enabled=cur.tree_locks_enabled
            if tree_locks_enabled is None
            else bool(tree_locks_enabled),
        )
        effective = _SETTINGS
    if reset_pool:
        with _POOL_GUARD:
            if _POOL is not None:
                _POOL.shutdown(wait=False, cancel_futures=True)
                _POOL = None
                _POOL_WORKERS = 0
    return effective


def reset_concurrency_settings() -> ConcurrencySettings:
    """Restore settings from environment (tests / process recycle)."""
    global _SETTINGS, _POOL, _POOL_WORKERS
    with _SETTINGS_GUARD:
        _SETTINGS = ConcurrencySettings.from_env()
        eff = _SETTINGS
    with _POOL_GUARD:
        if _POOL is not None:
            _POOL.shutdown(wait=False, cancel_futures=True)
            _POOL = None
            _POOL_WORKERS = 0
    return eff


def default_workers() -> int:
    """Sensible worker count (min 2, max 32), honoring ``max_workers`` policy."""
    s = get_concurrency_settings()
    if s.max_workers is not None:
        return max(1, min(32, int(s.max_workers)))
    n = os.cpu_count() or 4
    return max(2, min(32, n))


def should_parallelize(
    n_items: int,
    *,
    max_workers: Optional[int] = None,
    parallel: Optional[bool] = None,
) -> bool:
    """Whether multi-item helpers should use a pool (policy + kwargs)."""
    s = get_concurrency_settings()
    enabled = s.parallel_enabled if parallel is None else bool(parallel)
    if not enabled:
        return False
    workers = max_workers if max_workers is not None else s.max_workers
    if workers is not None and int(workers) <= 1:
        return False
    if n_items < s.min_items_for_parallel:
        return False
    if n_items <= 1:
        return False
    return True


def _shared_pool(max_workers: Optional[int] = None) -> ThreadPoolExecutor:
    global _POOL, _POOL_WORKERS
    want = max_workers if max_workers is not None else default_workers()
    want = max(1, int(want))
    with _POOL_GUARD:
        if _POOL is None or _POOL_WORKERS != want:
            if _POOL is not None:
                _POOL.shutdown(wait=False, cancel_futures=True)
            _POOL = ThreadPoolExecutor(
                max_workers=want,
                thread_name_prefix="uxdom-render",
            )
            _POOL_WORKERS = want
        return _POOL


def root_of(node: Any) -> Any:
    """Walk ``parent`` links to the tree root (cycle-safe)."""
    seen: set[int] = set()
    cur = node
    while True:
        parent = getattr(cur, "parent", None)
        if parent is None:
            return cur
        if not hasattr(parent, "children"):
            return cur
        cid = id(cur)
        if cid in seen:
            return cur
        seen.add(cid)
        cur = parent


def tree_lock_for(node: Any) -> threading.RLock:
    """Return the re-entrant lock for ``node``'s tree root."""
    root = root_of(node)
    key = id(root)

    with _LOCKS_GUARD:
        existing = _LOCKS.get(key)
        if existing is not None:
            return existing

    new_lock = threading.RLock()

    with _LOCKS_GUARD:
        existing = _LOCKS.get(key)
        if existing is not None:
            return existing
        _LOCKS[key] = new_lock

        def _clear(k: int = key) -> None:
            with _LOCKS_GUARD:
                cur = _LOCKS.get(k)
                if cur is new_lock:
                    _LOCKS.pop(k, None)

        try:
            weakref.finalize(root, _clear)
        except TypeError:
            pass
        return new_lock


@contextmanager
def multi_tree_lock(*nodes: Any) -> Iterator[None]:
    """Acquire root locks (no-op context if tree locks disabled by policy)."""
    if not get_concurrency_settings().tree_locks_enabled:
        yield
        return

    by_root: dict[int, threading.RLock] = {}
    for n in nodes:
        if n is None:
            continue
        if not hasattr(n, "children") and not hasattr(n, "parent"):
            continue
        try:
            root = root_of(n)
        except Exception:
            continue
        by_root[id(root)] = tree_lock_for(root)

    ordered = [by_root[k] for k in sorted(by_root.keys())]
    for lock in ordered:
        lock.acquire()
    try:
        yield
    finally:
        for lock in reversed(ordered):
            lock.release()


@contextmanager
def locked_tree(node: Any) -> Iterator[None]:
    with multi_tree_lock(node):
        yield


def _render_one(node: Any, pretty: bool) -> str:
    render = getattr(node, "__render__", None)
    if render is None:
        return str(node)
    return render(pretty=pretty)


def render_parallel(
    nodes: Sequence[Any],
    *,
    pretty: bool = False,
    max_workers: Optional[int] = None,
    parallel: Optional[bool] = None,
) -> list[str]:
    """Render many trees — parallel when policy allows, else sequential.

    Same signature and return type either way (usage pattern unchanged).
    """
    if not nodes:
        return []
    if not should_parallelize(len(nodes), max_workers=max_workers, parallel=parallel):
        return [_render_one(n, pretty) for n in nodes]

    workers = max_workers if max_workers is not None else min(default_workers(), len(nodes))
    workers = max(1, int(workers))
    if max_workers is not None:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="uxdom-rp") as ex:
            futs = [ex.submit(_render_one, n, pretty) for n in nodes]
            return [f.result() for f in futs]

    pool = _shared_pool(workers)
    futs = [pool.submit(_render_one, n, pretty) for n in nodes]
    return [f.result() for f in futs]


def build_parallel(
    fn: Callable[[T], R],
    items: Sequence[T],
    *,
    max_workers: Optional[int] = None,
    parallel: Optional[bool] = None,
) -> list[R]:
    """Map ``fn`` over items — parallel when policy allows, else sequential."""
    if not items:
        return []
    if not should_parallelize(len(items), max_workers=max_workers, parallel=parallel):
        return [fn(item) for item in items]
    workers = max_workers if max_workers is not None else min(default_workers(), len(items))
    workers = max(1, int(workers))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="uxdom-build") as ex:
        futs = [ex.submit(fn, item) for item in items]
        return [f.result() for f in futs]


def map_parallel(
    fn: Callable[[T], R],
    items: Iterable[T],
    *,
    max_workers: Optional[int] = None,
    parallel: Optional[bool] = None,
) -> list[R]:
    return build_parallel(fn, list(items), max_workers=max_workers, parallel=parallel)


async def render_async_gather(
    nodes: Sequence[Any],
    *,
    pretty: bool = False,
    chunk_size: int = 64,
    parallel: Optional[bool] = None,
) -> list[str]:
    """Async render many trees; sequential await when parallel policy is off."""
    if not nodes:
        return []

    async def one(node: Any) -> str:
        async_r = getattr(node, "__async_render__", None)
        if async_r is not None:
            parts: list[str] = []
            async for tok in async_r(pretty=pretty, chunk_size=chunk_size):
                parts.append(tok)
            return "".join(parts)
        return await asyncio.to_thread(_render_one, node, pretty)

    if not should_parallelize(len(nodes), parallel=parallel):
        out: list[str] = []
        for n in nodes:
            out.append(await one(n))
        return out
    return list(await asyncio.gather(*[one(n) for n in nodes]))
