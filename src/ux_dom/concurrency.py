# Copyright (c) 2026 UX-DOM
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Tree locks + internal parallel helpers for **ux-dom**.

**Application code should not import this for day-1 work.**
Render with ``node.__render__()`` / Document / routes. Concurrency is an
internal safety behaviour (per-root locks, safe defaults).

Maintainer tools: :mod:`ux_dom.profiling` and ``scripts/profile_p95.py``.
"""

from __future__ import annotations

from ux_dom.dom.src.concurrency import (  # noqa: F401
    ConcurrencySettings,
    build_parallel,
    configure_concurrency,
    default_workers,
    get_concurrency_settings,
    locked_tree,
    map_parallel,
    multi_tree_lock,
    render_async_gather,
    render_parallel,
    reset_concurrency_settings,
    root_of,
    should_parallelize,
    tree_lock_for,
)

__all__ = [
    "ConcurrencySettings",
    "configure_concurrency",
    "get_concurrency_settings",
    "reset_concurrency_settings",
    "should_parallelize",
    "root_of",
    "tree_lock_for",
    "multi_tree_lock",
    "locked_tree",
    "default_workers",
    "render_parallel",
    "build_parallel",
    "map_parallel",
    "render_async_gather",
]
