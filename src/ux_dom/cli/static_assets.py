# Copyright (c) 2026 ux-dom
"""Static shipping — prefer **single copy** from installed packages.

Library JS (ux_dom XElement, ux-channel, …) is served from site-packages via
``served_files``. ``uxdom build`` verifies packages; it does **not**
duplicate them into ``assets/`` by default.

App-local files (Tailwind CSS, user images) still live under ``assets/``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SyncedFile:
    rel: str
    path: Path
    sha256: str
    bytes: int
    action: str


@dataclass
class SyncReport:
    root: Path
    files: list[SyncedFile] = field(default_factory=list)
    mounts: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _default_hub(*, with_channel: bool = False):
    from ux_dom.plugins.hub import PluginHub
    from ux_dom.plugins.runtime import UxChannelRuntime, XElementRuntime

    hub = PluginHub()
    hub.add_contribution(XElementRuntime())  # package_mount default
    if with_channel:
        ch = UxChannelRuntime.optional()
        if ch is not None:
            hub.add_contribution(ch)
    return hub


def sync_runtime_assets(
    root: Path,
    *,
    hub: Any = None,
    with_channel: bool = False,
) -> SyncReport:
    """
    Prepare browser surface for an app root.

    Ensure hub has XElementRuntime; record package mount URLs; materialize
    **only** contributions that still use the webassets escape hatch.
    """
    root = Path(root).resolve()
    if hub is None:
        from ux_dom.plugins.hub import get_hub

        h = get_hub()
        if not h.contributions:
            h = _default_hub(with_channel=with_channel)
        hub = h

    report = SyncReport(root=root)
    try:
        for f in hub.served_static_files():
            report.mounts.append((f.url, str(f.path)))
            report.notes.append(f"safe file {f.url} → {f.path.name}")
    except Exception as e:
        report.errors.append(f"served_static_files: {e}")

    # Only materialize non-empty artifacts (explicit webassets escape hatch)
    rep = hub.materialize(root)
    for f in rep.files:
        report.files.append(
            SyncedFile(
                rel=f.disk_path,
                path=f.path,
                sha256=f.sha256,
                bytes=f.size,
                action=f.action,
            )
        )
    if not report.mounts and not report.files:
        report.notes.append("no package mounts or webassets artifacts on hub")
    return report
