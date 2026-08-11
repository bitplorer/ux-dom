"""Deep Playwright coverage: live xelement_kit + static XElement harness."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "examples" / "xelement_kit"
KIT_SUITE = ROOT / "tests" / "browser" / "kit_browser_suite.mjs"
STATIC_HARNESS = ROOT / "tests" / "browser" / "x_element_harness.mjs"
SHOT_KIT = ROOT / "screenshots" / "kit"
REPORT = SHOT_KIT / "browser-report.json"
NODE = os.environ.get("NODE_BIN", "node")


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_http(url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except Exception as e:
            last = e
            time.sleep(0.2)
    raise TimeoutError(f"server not up: {url} last={last}")


@unittest.skipUnless(KIT_SUITE.is_file(), "kit browser suite missing")
class TestKitBrowserDeep(unittest.TestCase):
    server: subprocess.Popen | None = None
    port: int = 0
    report: dict

    @classmethod
    def setUpClass(cls):
        SHOT_KIT.mkdir(parents=True, exist_ok=True)
        cls.port = _free_port()
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ROOT), str(KIT.resolve()), env.get("PYTHONPATH", "")]
        )
        # Start kit uvicorn
        cls.server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.port),
                "--log-level",
                "warning",
            ],
            cwd=str(KIT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        base = f"http://127.0.0.1:{cls.port}"
        try:
            _wait_http(base + "/health", timeout=25)
        except Exception:
            err = cls.server.stderr.read().decode() if cls.server.stderr else ""
            cls._teardown_server()
            raise RuntimeError(f"kit failed to start:\n{err}") from None

        env["KIT_URL"] = base
        env.setdefault("NODE_PATH", "/workspace/node_modules")
        proc = subprocess.run(
            [NODE, str(KIT_SUITE)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
        )
        cls.proc = proc
        cls.report = {}
        if REPORT.is_file():
            cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        if proc.returncode != 0 and not cls.report:
            cls._teardown_server()
            raise AssertionError(
                f"kit suite rc={proc.returncode}\nstdout={proc.stdout[-2500:]}\nstderr={proc.stderr[-2500:]}"
            )

    @classmethod
    def _teardown_server(cls):
        if cls.server and cls.server.poll() is None:
            cls.server.terminate()
            try:
                cls.server.wait(timeout=5)
            except Exception:
                cls.server.kill()
        cls.server = None

    @classmethod
    def tearDownClass(cls):
        cls._teardown_server()

    def test_suite_ok(self):
        self.assertEqual(
            self.proc.returncode,
            0,
            f"fails={self.report.get('fails')}\n{self.proc.stdout[-1500:]}",
        )
        self.assertTrue(self.report.get("ok"), self.report.get("fails"))

    def test_lightdom_upgraded_and_clickable(self):
        ld = self.report["phases"]["lightdom"]
        self.assertTrue(ld["defined"]["x-hello-light"])
        self.assertGreater(ld["upgraded"]["x-hello-light"]["childCount"], 0)
        self.assertIn("Clicked", ld.get("buttonAfterClick") or "")

    def test_shadowdom_has_shadow_roots(self):
        hosts = self.report["phases"]["shadowdom"]["hosts"]
        for tag, d in hosts.items():
            self.assertTrue(d["defined"], tag)
            self.assertTrue(d["hasShadow"], tag)

    def test_alpine_toggle_interactive(self):
        al = self.report["phases"]["alpine"]
        self.assertTrue(al["defined"])
        self.assertRegex(al["after"], r"ON|OFF")

    def test_htmx_swap_upgrades_x_hello(self):
        hx = self.report["phases"]["htmx"]["afterSwap"]
        self.assertTrue(hx["hasHost"])
        self.assertTrue(hx["defined"])
        self.assertTrue(hx["hostChildren"] > 0 or (hx.get("hostText") or ""))

    def test_slots_shadow_projection(self):
        sl = self.report["phases"]["slots"]
        self.assertTrue(sl["panelDefined"])
        self.assertTrue(sl["panelShadow"])

    def test_jinja_server_render(self):
        j = self.report["phases"]["jinja"]
        self.assertTrue(j["hasAlpha"])

    def test_screenshots_exist(self):
        shots = self.report.get("screenshots") or []
        self.assertGreaterEqual(len(shots), 6)
        for s in shots:
            p = Path(s)
            self.assertTrue(p.is_file(), s)
            self.assertGreater(p.stat().st_size, 400)


@unittest.skipUnless(STATIC_HARNESS.is_file(), "static harness missing")
class TestStaticHarnessStillGreen(unittest.TestCase):
    """Keep the offline fixture harness in the deep-browser gate."""

    def test_static_harness(self):
        env = os.environ.copy()
        env.setdefault("NODE_PATH", "/workspace/node_modules")
        # Don't require KIT_URL for static
        env.pop("KIT_URL", None)
        proc = subprocess.run(
            [NODE, str(STATIC_HARNESS)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout[-1500:] + proc.stderr[-500:])


if __name__ == "__main__":
    unittest.main()
