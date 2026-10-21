"""HTMX / Alpine support is attribute rendering only; Alpine helpers are opt-in.

ux-channel owns transport, so no HTMX runtime, routes, middleware or WebSocket
adapter ships here. Rendering itself is covered by test_alpine_dataset_merge
and test_hypermedia_surface.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

import ux_dom

ROOT = Path(__file__).resolve().parents[2]


class TestHtmxAlpineBoundary(unittest.TestCase):
    def test_import_ux_dom_does_not_load_alpine_helpers(self):
        code = (
            "import sys, ux_dom;"
            "print(sorted(m for m in sys.modules if m.startswith('ux_dom.alpinejs')))"
        )
        out = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(out, "[]")

    def test_transport_and_runtime_modules_absent(self):
        for mod in (
            "ux_dom.htmx",
            "ux_dom.web_io",
            "ux_dom.dom.src.ws_rpc",
            "ux_dom.plugins.control.htmx",
        ):
            with self.subTest(mod=mod):
                self.assertIsNone(importlib.util.find_spec(mod))
        self.assertFalse(hasattr(ux_dom, "Htmx"))


if __name__ == "__main__":
    unittest.main()
