"""XElement ↔ x_element.js contract, subclass matrix, host factory.

The kit pages are tested in tests/09_examples/test_xelement_kit.py.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ux_dom.dom import div, slot, template
from ux_dom.dom.htmlelement import (
    AlpineComponent,
    CustomElement,
    WebComponent,
)
from ux_dom.scripts import (
    x_element_js,
    x_element_js_text,
)

ROOT = Path(__file__).resolve().parents[2]
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


if __name__ == "__main__":
    unittest.main()
