"""Live browser: CustomElement / AlpineComponent login & signup flows.

Builds a Document with complex auth XElements, serves x_element.js + Alpine,
runs Chromium harness (validation, success, multi-instance, shadow shell).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ux_dom import Document
from ux_dom.dom import div, h1, p, script, span
from ux_dom.dom.htmlelement import xelement_registry
from ux_dom.plugins import XElementRuntime
from ux_dom.plugins.runtime import XELEMENT_JS_URL

from tests.fixtures.auth_xelements import (
    AuthShell,
    LoginForm,
    ProfileBadge,
    SessionBanner,
    SignupForm,
)

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "auth_xelement_harness.mjs"
X_JS = ROOT / "src" / "ux_dom" / "scripts" / "x_element.js"
SHOT = ROOT / "screenshots" / "auth-xelements"
NODE = os.environ.get("NODE_BIN", "node")


def _build_auth_page_html() -> str:
    """Full HTML document with definitions auto-collected + hosts + runtimes."""
    xelement_registry.clear()
    # Ensure definitions registered before document render
    for cls in (LoginForm, SignupForm, AuthShell, ProfileBadge, SessionBanner):
        cls.definition()

    doc = Document(
        head=[
            script(
                src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js",
                defer=True,
            ),
            script(src="/x_element.js", defer=True),
        ],
        body=[],
        ensure_csrf_token=False,
    )
    page = div(
        h1("Auth XElements live harness", className="text-xl font-bold mb-2"),
        p(
            "Login / Signup CustomElements upgraded by x_element.js + Alpine",
            className="text-sm text-slate-600 mb-4",
        ),
        SessionBanner(),
        div(
            ProfileBadge(),
            ProfileBadge(),
            ProfileBadge(),
            className="flex gap-2 mb-4",
            id="badges",
        ),
        AuthShell(
            span("UxDom Auth", **{"slot": "header"}),
            div(
                LoginForm(),
                LoginForm(),  # second instance — independent Alpine state
                className="grid gap-4 md:grid-cols-2 mb-4",
                id="login-row",
            ),
            SignupForm(),
            id="shell-body",
        ),
        id="auth-app",
        className="mx-auto max-w-3xl p-6 font-sans",
    )
    return str(doc(page))


@unittest.skipUnless(HARNESS.is_file() and X_JS.is_file(), "auth harness or x_element.js missing")
class TestAuthCustomElementsLiveBrowser(unittest.TestCase):
    def test_login_signup_live_upgrade_and_behaviour(self):
        SHOT.mkdir(parents=True, exist_ok=True)
        html = _build_auth_page_html()
        # Sanity: templates + hosts present server-side
        self.assertIn('x-tagname="login-form"', html)
        self.assertIn('x-tagname="signup-form"', html)
        self.assertIn("<x-login-form", html)
        self.assertIn("<x-signup-form", html)
        self.assertIn("<x-auth-shell", html)
        self.assertGreaterEqual(html.count("<x-login-form"), 2)
        self.assertGreaterEqual(html.count("<x-profile-badge"), 3)

        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write(html)
            html_path = f.name

        env = os.environ.copy()
        env["AUTH_HTML_PATH"] = html_path
        env["AUTH_JS_PATH"] = str(X_JS)
        proc = subprocess.run(
            [NODE, str(HARNESS)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )
        if proc.returncode != 0:
            self.fail(
                "auth browser harness failed\n"
                f"stdout:\n{proc.stdout[-3000:]}\n"
                f"stderr:\n{proc.stderr[-2000:]}"
            )
        # report file
        report = SHOT / "auth-browser-report.json"
        self.assertTrue(report.is_file(), "missing auth-browser-report.json")
        text = report.read_text()
        self.assertIn('"ok": true', text.replace(" ", "").replace("true", " true") or text)
        # more reliable
        import json

        data = json.loads(text)
        self.assertTrue(data.get("ok"), data.get("fails"))


@unittest.skipUnless(HARNESS.is_file(), "harness missing")
class TestAuthPageMarkupOnly(unittest.TestCase):
    """Fast path without browser — structure guarantees for CI without Chromium."""

    def test_definitions_deduped_in_document(self):
        xelement_registry.clear()
        html = _build_auth_page_html()
        self.assertEqual(html.count('x-tagname="login-form"'), 1)
        self.assertEqual(html.count('x-tagname="signup-form"'), 1)
        self.assertEqual(html.count('x-tagname="auth-shell"'), 1)
        self.assertEqual(html.count('x-tagname="profile-badge"'), 1)


if __name__ == "__main__":
    unittest.main()
