"""Headless Chromium (Playwright) verification of x_element.js / XElement."""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "x_element_harness.mjs"
SHOT_DIR = ROOT / "screenshots"
REPORT = SHOT_DIR / "xelement-browser-report.json"
NODE = os.environ.get("NODE_BIN", "node")


@unittest.skipUnless(HARNESS.is_file(), "browser harness missing")
class TestXElementHeadlessBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        # Prefer workspace playwright module path used by harness
        env = os.environ.copy()
        env.setdefault("NODE_PATH", "/workspace/node_modules")
        proc = subprocess.run(
            [NODE, str(HARNESS)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        cls.proc = proc
        cls.report = {}
        if REPORT.is_file():
            try:
                cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
            except Exception:
                cls.report = {}
        if proc.returncode != 0 and not cls.report:
            raise AssertionError(
                f"harness failed rc={proc.returncode}\n"
                f"stdout={proc.stdout[-2000:]}\nstderr={proc.stderr[-2000:]}"
            )

    def test_harness_exit_ok(self):
        self.assertEqual(
            self.proc.returncode,
            0,
            f"fails={self.report.get('fails')}\nstderr={self.proc.stderr[-1000:]}",
        )

    def test_report_ok_flag(self):
        self.assertTrue(self.report.get("ok"), self.report.get("fails"))

    def test_no_page_errors(self):
        self.assertEqual(self.report.get("pageErrors") or [], [])

    def test_custom_element_upgraded(self):
        initial = self.report["phases"]["initial"]
        self.assertTrue(initial["defined"]["hello"])
        self.assertTrue(initial["hello"]["hasInner"])
        self.assertIn("Hello", initial["hello"]["childText"])

    def test_shadow_dom_and_slot(self):
        shadow = self.report["phases"]["initial"]["shadow"]
        self.assertTrue(shadow["hasShadowRoot"])
        self.assertIn("Shadow", shadow["shadowText"])
        # light DOM projection present
        self.assertTrue(shadow["projectedVisible"])
        flat = str(shadow.get("slotAssigned"))
        self.assertIn("projected light", flat)

    def test_alpine_toggle_host(self):
        initial = self.report["phases"]["initial"]
        self.assertTrue(initial["defined"]["toggle"])
        self.assertTrue(initial["toggle"]["hasXData"])
        # after click phase
        after = self.report["phases"].get("afterToggleClick") or initial
        self.assertIn(after["toggle"]["text"], ("ON", "OFF"))

    def test_dynamic_inject_defines_x_dyn(self):
        dyn = self.report["phases"]["afterDynamic2"]["dyn"]
        self.assertTrue(dyn["defined"])
        self.assertIn("dynamic", dyn["text"])

    def test_screenshots_written(self):
        shots = self.report.get("screenshots") or []
        self.assertGreaterEqual(len(shots), 3)
        for s in shots:
            p = Path(s)
            self.assertTrue(p.is_file(), s)
            self.assertGreater(p.stat().st_size, 500)

    def test_contract_attr_tag(self):
        self.assertEqual(self.report["phases"]["initial"]["attrTag"], "x-tagname")


if __name__ == "__main__":
    unittest.main()
