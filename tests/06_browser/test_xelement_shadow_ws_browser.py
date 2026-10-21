"""Headless Chromium: x_element.js reads only ``shadowroot``; WebSocket path intact.

The harness serves the page and every WebSocket from Playwright routes, so it
needs no network and no CDN.
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from browser_gate import NODE, require_browser

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "x_element_shadow_ws_harness.mjs"


class TestXElementShadowAndWs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_browser()
        proc = subprocess.run(
            [NODE, str(HARNESS)], cwd=str(ROOT), capture_output=True, text=True, timeout=120
        )
        if proc.returncode != 0:
            raise AssertionError(f"harness rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}")
        cls.report = json.loads(proc.stdout)
        cls.dom = cls.report["dom"]
        cls.sockets = cls.report["sockets"]

    def test_no_page_errors(self):
        self.assertEqual(self.report["pageErrors"], [])

    def test_shadowroot_true_attaches_open_shadow(self):
        sr = self.dom["srOpen"]
        self.assertTrue(sr["openShadowRoot"])
        self.assertEqual(sr["shadowText"], "open shadow")
        self.assertEqual(sr["lightText"], "projected")

    def test_shadowroot_closed_attaches_closed_shadow(self):
        sr = self.dom["srClosed"]
        self.assertFalse(sr["openShadowRoot"])
        self.assertTrue(sr["runtimeShadow"])

    def test_shadowdom_is_not_a_shadow_attribute(self):
        sd = self.dom["sdOnly"]
        self.assertFalse(sd["openShadowRoot"])
        self.assertFalse(sd["runtimeShadow"])
        self.assertEqual(sd["lightText"], "synonym")

    def test_light_element_has_no_shadow(self):
        self.assertFalse(self.dom["light"]["runtimeShadow"])
        self.assertEqual(self.dom["light"]["lightText"], "light body")

    def test_ws_message_echoed_and_closed_on_disconnect(self):
        live = self.sockets["/ws-live"]
        self.assertEqual(live["opened"], 1)
        self.assertEqual(
            [json.loads(m) for m in live["received"]],
            [{"id": "live", "attr": "count", "oldVal": "0", "newVal": "5"}],
        )
        self.assertTrue(live["closed"])

    def test_ws_send_attribute_sends_nothing_on_connect(self):
        sender = self.sockets["/ws-send"]
        self.assertEqual(sender["opened"], 1)
        self.assertEqual(sender["received"], [])


if __name__ == "__main__":
    unittest.main()
