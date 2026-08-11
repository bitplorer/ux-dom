"""XElement ↔ x_element.js contract, subclass matrix, host factory, kit smoke."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from ux_dom.dom import div, slot, template
from ux_dom.dom.htmlelement import (
    AlpineComponent,
    CustomElement,
    WebComponent,
    XElement,
)
from ux_dom.scripts import (
    x_element_js,
    x_element_js_text,
)

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "examples" / "xelement_kit"
RUNTIME_JS = ROOT / "src" / "ux_dom" / "scripts" / "x_element.js"


class TestXElementContract(unittest.TestCase):
    """Single-name / single-attr runtime identity."""

    def test_runtime_file_on_disk(self):
        self.assertTrue(RUNTIME_JS.is_file())
        self.assertGreater(RUNTIME_JS.stat().st_size, 50)

    def test_runtime_source_tokens(self):
        src = x_element_js_text()
        self.assertEqual(src, RUNTIME_JS.read_text(encoding="utf-8"))
        self.assertIn("x-tagname", src)
        self.assertIn("UxDom.XElement", src)
        self.assertIn("customElements.define", src)
        self.assertIn("htmx:afterSwap", src)
        self.assertIn("ATTR_TAG", src)
        self.assertNotIn("ATTR_TAG_LEGACY", src)
        # header documents the contract
        head = "\n".join(src.splitlines()[:25])
        self.assertIn("x_element.js", head)
        self.assertIn("XElement", head)
        self.assertIn("x-tagname", head)

    def test_helper_renders_runtime(self):
        rendered = str(x_element_js())
        self.assertIn("x-tagname", rendered)
        self.assertIn("customElements.define", rendered)

    def test_save_writes_js_file(self):
        with TemporaryDirectory() as td:
            dest = Path(td)
            name = x_element_js().save(file_or_dir=dest)
            self.assertEqual(name, "x_element_js.js")
            path = dest / name
            self.assertTrue(path.is_file())
            text = path.read_text(encoding="utf-8")
            self.assertIn("x-tagname", text)
            self.assertIn("UxDom.XElement", text)

    @unittest.skipUnless(shutil.which("node"), "node not available")
    def test_runtime_js_parses_in_node(self):
        """Syntax-check x_element.js (no browser APIs exercised)."""
        # Provide minimal browser stubs so the IIFE can evaluate
        stub = r"""
        global.document = {
          location: { href: 'http://localhost/', protocol: 'http:', host: 'localhost' },
          readyState: 'complete',
          querySelectorAll: () => [],
          addEventListener: () => {},
          body: null,
        };
        global.window = global;
        global.HTMLElement = class HTMLElement {};
        global.customElements = { get: () => undefined, define: () => {} };
        global.MutationObserver = class { observe() {} disconnect() {} };
        global.CustomEvent = class CustomEvent { constructor(n, o) { this.type=n; this.detail=o&&o.detail; } };
        global.WebSocket = class WebSocket {
          constructor() { this.readyState = 1; }
          addEventListener() {}
          send() {}
          close() {}
        };
        WebSocket.OPEN = 1;
        """
        script = stub + "\n" + RUNTIME_JS.read_text(encoding="utf-8") + "\n"
        script += "if (!global.UxDom || !global.UxDom.XElement) process.exit(2);\n"
        script += (
            "if (global.UxDom.XElement.ATTR_TAG !== 'x-tagname') process.exit(3);\n"
        )
        with TemporaryDirectory() as td:
            f = Path(td) / "check.js"
            f.write_text(script, encoding="utf-8")
            proc = subprocess.run(
                ["node", str(f)],
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(
                proc.returncode,
                0,
                f"stdout={proc.stdout!r} stderr={proc.stderr!r}",
            )


class TestPythonXElementAttrs(unittest.TestCase):
    """Definition attribute + subclass check matrix."""

    def test_requires_x_tagname(self):
        class Bad(CustomElement):
            tag_name = "bad"

            def render(self, tag_name: str = "bad"):
                return div("no tag")

        with self.assertRaises(AttributeError) as ctx:
            Bad.definition()
        self.assertIn("x-tagname", str(ctx.exception))

    def test_x_tagname_ok_on_custom_element(self):
        class Ok(CustomElement):
            tag_name = "hi"

            def render(self, tag_name: str = "hi"):
                return template(div("hi"), **{"x-tagname": tag_name})

        html = str(Ok.definition())
        self.assertIn("x-tagname", html)
        self.assertIn('x-tagname="hi"', html)
        self.assertIn("<x-hi", str(Ok()))

    def test_x_component_attr_rejected(self):
        class Leg(CustomElement):
            tag_name = "hi"

            def render(self, tag_name: str = "hi"):
                return template(div("hi"), **{"x-component": tag_name})

        with self.assertRaises(AttributeError) as ctx:
            Leg.definition()
        self.assertIn("x-tagname", str(ctx.exception))

    def test_custom_element_forbids_shadow(self):
        class CBad(CustomElement):
            tag_name = "c"

            def render(self, tag_name: str = "c"):
                return template(
                    div("x"), **{"x-tagname": tag_name, "shadowroot": "true"}
                )

        with self.assertRaises(AttributeError) as ctx:
            CBad.definition()
        msg = str(ctx.exception).lower()
        self.assertTrue("shadowroot" in msg or "shadowdom" in msg)

    def test_webcomponent_requires_shadow(self):
        class WBad(WebComponent):
            def render(self, tag_name):
                return template(div("x"), **{"x-tagname": tag_name})

        with self.assertRaises(AttributeError) as ctx:
            WBad("w")
        msg = str(ctx.exception).lower()
        self.assertTrue("shadowroot" in msg or "shadowdom" in msg)

    def test_webcomponent_shadow_ok(self):
        class W(WebComponent):
            tag_name = "w"

            def render(self, tag_name: str = "w"):
                return template(
                    div(slot()), **{"x-tagname": tag_name, "shadowroot": "true"}
                )

        html = str(W.definition())
        self.assertIn("shadowroot", html)
        self.assertIn("<x-w", str(W()))

    def test_alpine_ok(self):
        class A(AlpineComponent):
            tag_name = "a"

            def render(self, tag_name: str = "a"):
                return template(
                    div(**{"x-data": "{n:0}"}),
                    **{"x-tagname": tag_name},
                )

        html = str(A.definition())
        self.assertIn("x-data", html)
        self.assertIn('x-tagname="a"', html)


class TestXElementHostFactory(unittest.TestCase):
    """Class = definition registry; constructor = host."""

    def test_call_emits_x_prefixed_host_tag(self):
        class Toggle(CustomElement):
            tag_name = "toggle"

            def render(self, tag_name: str = "toggle"):
                return template(div("body"), **{"x-tagname": tag_name})

        def_html = str(Toggle.definition())
        self.assertIn("<template", def_html)
        self.assertIn('x-tagname="toggle"', def_html)

        host = Toggle()
        host_html = str(host)
        self.assertIn("<x-toggle", host_html)
        self.assertNotIn("x-tagname", host_html)

    def test_definition_and_host_name_sync(self):
        class Hello(CustomElement):
            tag_name = "hello-card"

            def render(self, tag_name: str = "hello-card"):
                return template(div("hi"), **{"x-tagname": tag_name})

        name = "hello-card"
        definition = Hello.definition()
        m = re.search(r'x-tagname="([^"]+)"', str(definition))
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), name)
        host_html = str(Hello())
        self.assertIn(f"<x-{name}", host_html)


class TestXElementKit(unittest.TestCase):
    """Production-shaped example app (HTMX / Alpine / Web Components)."""

    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls._kit_path = str(KIT.resolve())
        if cls._kit_path not in sys.path:
            sys.path.insert(0, cls._kit_path)
        for k in list(sys.modules):
            if k == "app" or k.startswith("app."):
                del sys.modules[k]
        from app.main import app

        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        for k in list(sys.modules):
            if k == "app" or k.startswith("app."):
                del sys.modules[k]
        if getattr(cls, "_kit_path", None) in sys.path:
            sys.path.remove(cls._kit_path)

    def test_health_runtime_name(self):
        h = self.client.get("/health").json()
        self.assertTrue(h["ok"])
        self.assertEqual(h.get("runtime"), "x_element.js")
        self.assertEqual(h.get("python"), "XElement")

    def test_serves_x_element_js(self):
        js = self.client.get("/ux-dom/static/x_element.js")
        self.assertEqual(js.status_code, 200)
        self.assertIn("customElements.define", js.text)
        self.assertIn("x-tagname", js.text)
        # same contract as package runtime
        self.assertIn("UxDom.XElement", js.text)

    def test_wc_page_definition_and_host(self):
        r = self.client.get("/wc/WcDemo")
        self.assertEqual(r.status_code, 200)
        self.assertIn("x-tagname", r.text)
        self.assertIn("x-hello", r.text)
        self.assertIn("x-shadow-card", r.text)
        self.assertIn("x_element.js", r.text)

    def test_alpine_page(self):
        r = self.client.get("/alpine/AlpineDemo")
        self.assertEqual(r.status_code, 200)
        self.assertIn("x-tagname", r.text)
        self.assertIn("x-toggle", r.text)
        self.assertIn("x-counter", r.text)
        self.assertIn("x_element.js", r.text)

    def test_htmx_demo_and_partial(self):
        demo = self.client.get("/htmx/HtmxDemo")
        self.assertEqual(demo.status_code, 200)
        self.assertIn("hx-get", demo.text.lower() or demo.text)
        # partial may include definition + host
        partial = self.client.get("/htmx/Partial")
        self.assertEqual(partial.status_code, 200)
        self.assertTrue(
            "x-tagname" in partial.text or "x-hello" in partial.text,
            partial.text[:300],
        )

    def test_light_and_shadow_galleries(self):
        light = self.client.get("/lightdom/LightDomDemo")
        self.assertEqual(light.status_code, 200)
        self.assertIn("Light DOM", light.text)
        self.assertIn("x-tagname", light.text)
        self.assertIn("hello-light", light.text)
        self.assertIn("x_element.js", light.text)
        shadow = self.client.get("/shadowdom/ShadowDomDemo")
        self.assertEqual(shadow.status_code, 200)
        self.assertIn("Shadow DOM", shadow.text)
        self.assertIn("shadowroot", shadow.text)
        self.assertIn("profile-card", shadow.text)
        self.assertIn("x_element.js", shadow.text)


if __name__ == "__main__":
    unittest.main()
