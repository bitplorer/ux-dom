"""Shared pytest fixtures for ux-dom.

Test tree ontology
------------------
| Package | Concern |
|---------|---------|
| ``01_core`` | DOM, Component, membership, render, reactive |
| ``02_document_plugins`` | Document, CSP, XElement, UI kit, plugins |
| ``03_routing_cli`` | Scaffold, CLI, build, deploy |
| ``04_production`` | Hardening, readiness, examples, standalone |
| ``05_chaos`` | Pentest, stress, race, parsing chaos |
| ``06_browser`` | Live Chromium / kit / auth custom elements |
| ``fixtures/`` | Shared DOM fixtures (e.g. auth xelements) |
| ``browser/`` | Playwright harness JS (not collected as tests) |

Discovery order follows directory name prefixes (``01``…``06``).
Within each module, test method order is preserved (do not reorder casually).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ux_dom.plugins import hub as plugin_hub

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Repository root (parent of ``tests/``)."""
    return REPO_ROOT


@pytest.fixture(autouse=True)
def _isolate_plugin_hub(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restore the process-global plugin hub after each test.

    ``set_hub`` (and ``App.build`` / ``App.mount``) replace a module global;
    without this, a hub registered by one test leaks into later ones.
    Function scope only: hubs set in ``setUpClass`` or at import time are
    not covered.
    """
    monkeypatch.setattr(plugin_hub, "_default_hub", plugin_hub._default_hub)
