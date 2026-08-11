"""CSP — middleware-owned nonce lifecycle (least-confusion model)."""

from __future__ import annotations

import re
import unittest

from fastapi import FastAPI
from fastapi.responses import HTMLResponse as FastAPIHTMLResponse
from fastapi.testclient import TestClient

from ux_dom.dom import div, script
from ux_dom.plugins import App, Csp, XElementRuntime, shell_fragments
from ux_dom.plugins.csp import (
    build_csp_header,
    generate_nonce,
    get_nonce,
    reset_nonce,
    set_nonce,
    stamp_nonce,
    stamp_tree,
)
from ux_dom.plugins.host import FastAPIHost
from ux_dom.plugins.hub import PluginHub, set_hub
from ux_dom.plugins.runtime import XELEMENT_JS_URL
from ux_dom.response.starlette import HTMLResponse


class TestNonceCrypto(unittest.TestCase):
    def test_unique(self):
        self.assertNotEqual(generate_nonce(), generate_nonce())


class TestStamp(unittest.TestCase):
    def test_stamp_script(self):
        tok = set_nonce("abc")
        try:
            n = script(src=XELEMENT_JS_URL, defer=True)
            stamp_nonce([n])
            self.assertIn('nonce="abc"', str(n))
        finally:
            reset_nonce(tok)

    def test_stamp_tree_nested(self):
        tok = set_nonce("t1")
        try:
            tree = div(script(src="/a.js"), div(script(src="/b.js")))
            stamp_tree(tree)
            html = str(tree)
            self.assertEqual(html.count('nonce="t1"'), 2)
        finally:
            reset_nonce(tok)


class TestHeader(unittest.TestCase):
    def test_build(self):
        h = build_csp_header(
            "n1", strict_dynamic=True, script_hosts=["https://unpkg.com"]
        )
        self.assertIn("'nonce-n1'", h)
        self.assertIn("'strict-dynamic'", h)


class TestMiddlewareIsEnough(unittest.TestCase):
    """App().use(Csp()) — header + stamped shell fragments, no extra wiring."""

    def test_use_csp_once(self):
        set_hub(PluginHub())
        builder = (
            App()
            .use(XElementRuntime())
            .use(Csp(debug_header=True))
            .use(FastAPIHost(title="csp", debug=True))
        )
        app = builder.build()

        @app.get("/page")
        def page():
            head, _ = shell_fragments(builder.hub)
            return "\n".join(str(x) for x in head) + "\n" + str(div("hi"))

        c = TestClient(app)
        r = c.get("/page")
        self.assertEqual(r.status_code, 200)
        csp = r.headers.get("content-security-policy")
        self.assertIsNotNone(csp)
        m = re.search(r"'nonce-([^']+)'", csp)
        self.assertIsNotNone(m, csp)
        nonce = m.group(1)
        self.assertIn(f'nonce="{nonce}"', r.text)
        self.assertEqual(r.headers.get("x-ux_dom-csp-nonce"), nonce)

    def test_html_response_stamps_tree(self):
        """ux_dom HTMLResponse stamps even without shell_fragments."""
        set_hub(PluginHub())
        app = App().use(Csp(debug_header=True)).use(FastAPIHost(title="t")).build()

        @app.get("/dom")
        def dom():
            return HTMLResponse(div(script(src="/app.js"), "x"))

        r = TestClient(app).get("/dom")
        csp = r.headers.get("content-security-policy")
        nonce = re.search(r"'nonce-([^']+)'", csp).group(1)
        self.assertIn(f'nonce="{nonce}"', r.text)
        self.assertIn("/app.js", r.text)


if __name__ == "__main__":
    unittest.main()
