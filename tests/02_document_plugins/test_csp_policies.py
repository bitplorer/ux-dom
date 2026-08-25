"""CSP presets, knobs, strict-dynamic host semantics locks."""

from __future__ import annotations

import re
import unittest

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from ux_dom.dom import div, script
from ux_dom.plugins import App, Csp
from ux_dom.plugins.csp import (
    build_csp_header,
    policy_dev,
    policy_prod,
    policy_report_only,
)
from ux_dom.plugins.hub import PluginHub, set_hub
from ux_dom.response.starlette import HTMLResponse


class TestBuildHeader(unittest.TestCase):
    def test_style_unsafe_inline(self):
        h = build_csp_header("n", style_unsafe_inline=True)
        self.assertIn("style-src", h)
        # style-src should include unsafe-inline when flag set
        m = re.search(r"style-src ([^;]+)", h)
        self.assertIsNotNone(m)
        self.assertIn("'unsafe-inline'", m.group(1))

    def test_extra_directives(self):
        h = build_csp_header("n", extra_directives={"frame-src": "'none'"})
        self.assertIn("frame-src 'none'", h)

    def test_form_action_default(self):
        h = build_csp_header("n")
        self.assertIn("form-action 'self'", h)

    def test_strict_dynamic_hosts_present_in_string(self):
        """Hosts remain in the header string for legacy; modern browsers ignore under strict-dynamic."""
        h = build_csp_header(
            "n",
            strict_dynamic=True,
            script_hosts=["https://unpkg.com"],
        )
        self.assertIn("'strict-dynamic'", h)
        self.assertIn("https://unpkg.com", h)
        self.assertIn("'nonce-n'", h)


class TestPresets(unittest.TestCase):
    def test_dev(self):
        p = policy_dev()
        self.assertTrue(p.style_unsafe_inline)
        self.assertIn("https://unpkg.com", p.script_hosts)
        h = p.build("X")
        self.assertIn("https://cdn.tailwindcss.com", h)
        self.assertIn("'unsafe-inline'", re.search(r"style-src ([^;]+)", h).group(1))

    def test_prod(self):
        p = policy_prod()
        self.assertEqual(p.script_hosts, ())
        self.assertFalse(p.style_unsafe_inline)
        self.assertTrue(p.upgrade_insecure)
        h = p.build("X")
        self.assertNotIn("unpkg.com", h)
        self.assertIn("upgrade-insecure-requests", h)
        self.assertIn("worker-src", h)

    def test_report_only_flag(self):
        p = policy_report_only()
        self.assertTrue(p.report_only)

    def test_auto_follows_debug(self):
        self.assertTrue(Csp.auto(debug=True).style_unsafe_inline)
        self.assertEqual(list(Csp.auto(debug=False).script_hosts), [])

    def test_csp_classmethods(self):
        self.assertTrue(Csp.dev().style_unsafe_inline)
        self.assertEqual(list(Csp.prod().script_hosts), [])
        self.assertTrue(Csp.report_only().is_report_only)


class TestMiddlewarePresets(unittest.TestCase):
    def test_prod_header(self):
        set_hub(PluginHub())
        app = App().use(Csp.prod(debug_header=True)).build(asgi=FastAPI(title="t", default_response_class=HTMLResponse))

        @app.get("/")
        def home():
            return HTMLResponse(div(script(src="/a.js")))

        r = TestClient(app).get("/")
        csp = r.headers.get("content-security-policy")
        self.assertIsNotNone(csp)
        self.assertNotIn("unpkg.com", csp)
        self.assertIn("form-action", csp)
        self.assertIn("'nonce-", csp)
        self.assertIn('nonce="', r.text)

    def test_report_only_header_name(self):
        set_hub(PluginHub())
        app = (
            App()
            .use(Csp.report_only(debug_header=True))
            .build(asgi=FastAPI(title="t", default_response_class=HTMLResponse))
        )

        @app.get("/")
        def home():
            return HTMLResponse(div("x"))

        r = TestClient(app).get("/")
        self.assertIsNone(r.headers.get("content-security-policy"))
        ro = r.headers.get("content-security-policy-report-only")
        self.assertIsNotNone(ro)
        self.assertIn("'nonce-", ro)

    def test_dev_has_cdn_and_style_inline(self):
        set_hub(PluginHub())
        app = App().use(Csp.dev()).build(asgi=FastAPI(title="t", default_response_class=HTMLResponse))

        @app.get("/")
        def home():
            return "ok"

        r = TestClient(app).get("/")
        csp = r.headers.get("content-security-policy")
        self.assertIn("unpkg.com", csp)
        style = re.search(r"style-src ([^;]+)", csp).group(1)
        self.assertIn("'unsafe-inline'", style)


if __name__ == "__main__":
    unittest.main()
