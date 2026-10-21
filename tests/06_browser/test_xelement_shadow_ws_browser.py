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

BENIGN = {"count": "5", "data-count": "5", "aria-label": "new", "value": "new"}
DECLARED_REFUSED = {
    "href": "/old",
    "src": "/old",
    "action": "/old",
    "formaction": "/old",
    "xlink:href": "/old",
    "hx-get": "/old",
    "srcset": "/old.png",
    "srcdoc": "old",
    "style": "color: red",
    "onclick": "void 0",
}


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
        self.assertEqual([json.loads(m) for m in live["received"]], self.report["liveMessages"])
        self.assertTrue(live["closed"])

    def test_ws_message_is_applied_to_the_dom(self):
        # Received is not enough: a benign declared attribute takes the new value.
        live = self.dom["live"]
        for attr, value in BENIGN.items():
            with self.subTest(attr):
                self.assertEqual(live[attr], value)

    def test_ws_message_cannot_set_url_style_srcdoc_or_handler(self):
        # #107's URL policy is Python-only, so the runtime refuses these names
        # outright; the declared value stays.
        live = self.dom["live"]
        for attr, value in DECLARED_REFUSED.items():
            with self.subTest(attr):
                self.assertEqual(live[attr], value)
        self.assertNotIn("data-new", live)  # undeclared: never added

    def test_each_refused_message_warns_and_keeps_the_socket(self):
        refused = [m["attr"] for m in self.report["liveMessages"] if m["attr"] not in BENIGN]
        warned = [w for w in self.report["warnings"] if "ws message" in w]
        self.assertEqual(len(warned), len(refused))
        for attr in refused:
            with self.subTest(attr):
                self.assertTrue(any(json.dumps(attr) in w for w in warned))
        self.assertEqual(self.report["pageErrors"], [])

    def test_ws_send_attribute_sends_nothing_on_connect(self):
        sender = self.sockets["/ws-send"]
        self.assertEqual(sender["opened"], 1)
        self.assertEqual(sender["received"], [])


if __name__ == "__main__":
    unittest.main()
