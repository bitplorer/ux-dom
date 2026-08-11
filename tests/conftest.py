"""Shared pytest fixtures for uxdom 0.1.

Test tree ontology
------------------
| Package | Concern |
|---------|---------|
| ``01_core`` | DOM, Component, membership, render, reactive |
| ``02_document_plugins`` | Document, CSP, XElement, UI kit, plugins |
| ``03_routing_cli`` | Router, scaffold, CLI, build, deploy |
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

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Repository root (parent of ``tests/``)."""
    return REPO_ROOT
