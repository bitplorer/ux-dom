"""Playwright against the live example apps (htmx under CSP, SSE, WebSocket,
ux-channel actions, user-content escaping).

Boots each app with uvicorn from the repo root, then runs
tests/browser/examples_suite.mjs once and checks its JSON report.
"""

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

from browser_gate import NODE, require_browser
from channel_gate import require_channel

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "tests" / "browser" / "examples_suite.mjs"
APPS = {
    "SHOWCASE_URL": "examples.showcase.main:app",
    "CHANNEL_URL": "examples.ux_channel_counter.main:app",
    "WS_URL": "examples.standalone.ws:app",
    "SEARCH_URL": "examples.standalone.search:app",
}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_http(url: str, timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    while True:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except OSError:
            if time.time() > deadline:
                raise
            time.sleep(0.2)


class TestExamplesBrowser(unittest.TestCase):
    servers: list[subprocess.Popen]
    report: dict

    @classmethod
    def setUpClass(cls):
        require_browser()
        require_channel()
        cls.servers = []
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
        try:
            for var, target in APPS.items():
                port = _free_port()
                cls.servers.append(
                    subprocess.Popen(
                        [
                            sys.executable,
                            "-m",
                            "uvicorn",
                            target,
                            "--port",
                            str(port),
                            "--host",
                            "127.0.0.1",
                            "--log-level",
                            "warning",
                        ],
                        cwd=ROOT,
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                )
                env[var] = f"http://127.0.0.1:{port}"
                _wait_http(env[var] + "/health")
            proc = subprocess.run(
                [NODE, str(SUITE)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=240,
            )
        except BaseException:
            cls._stop()
            raise
        cls.proc = proc
        lines = proc.stdout.strip().splitlines()
        cls.report = json.loads(lines[-1]) if lines else {}

    @classmethod
    def _stop(cls):
        for server in cls.servers:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()

    @classmethod
    def tearDownClass(cls):
        cls._stop()

    def test_suite_passed(self):
        self.assertTrue(
            self.report.get("ok"),
            f"fails={self.report.get('fails')}\nstderr={self.proc.stderr[-1500:]}",
        )
        self.assertEqual(self.proc.returncode, 0)

    def test_showcase_htmx_sse_and_escaping(self):
        show = self.report["phases"]["showcase"]
        self.assertTrue(show["cart"]["sameDoc"])
        self.assertIsNone(show["guestbook"]["pwned"])
        self.assertEqual(show["guestbook"]["imgs"], 0)
        self.assertRegex(show["sse"], r"tick #\d+")
        self.assertEqual(show["csp"], [])

    def test_channel_action_and_forgery(self):
        counts = self.report["phases"]["channel"]["counts"]
        self.assertEqual(counts["afterForged"], counts["start"] + 5)
        self.assertEqual(self.report["phases"]["channel"]["csp"], [])

    def test_websocket_client(self):
        self.assertEqual(self.report["phases"]["ws"]["n"], "2")
        self.assertEqual(self.report["phases"]["ws"]["csp"], [])

    def test_search_partial(self):
        result = self.report["phases"]["search"]["result"]
        self.assertEqual((result["first"], result["hits"]), ("kiwi-0", 30))


if __name__ == "__main__":
    unittest.main()
