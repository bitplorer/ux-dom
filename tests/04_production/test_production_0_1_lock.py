"""0.1 production lock — ux-dom contracts that must not regress.

Locks:

* package version ``0.1.0``
* ``x_element.js`` package mount + no legacy WS globals
* soft ``UxChannelRuntime`` (tags only by default)
* ``Channel`` alias is Document plugin, not action plane
* no ``html_elements`` / ``x_component_js`` script aliases
"""

from __future__ import annotations

import unittest
import ux_dom
from ux_dom import Document
from ux_dom.runtime import XElement, Htmx, Csp
from ux_dom.plugins.runtime import UxChannelRuntime, XELEMENT_JS_URL
from ux_dom.scripts import x_element_js_text


class TestBrandAndVersion(unittest.TestCase):
    def test_version_0_1(self):
        self.assertEqual(ux_dom.__version__, "0.1.0")


class TestDocumentRuntimes(unittest.TestCase):
    def test_document_use_core_runtimes(self):
        doc = Document(head=[], body=[]).use(XElement(), Htmx(), Csp.auto())
        html = str(doc) if hasattr(doc, "__str__") else None
        # at least constructs
        self.assertIsNotNone(doc)

    def test_xelement_url_is_package_mount(self):
        self.assertTrue(XELEMENT_JS_URL.startswith("/ux-dom/static/"))
        self.assertIn("x_element.js", XELEMENT_JS_URL)

    def test_x_element_js_has_no_legacy_globals(self):
        src = x_element_js_text()
        self.assertIn("ux_domMessageHandler", src)
        self.assertIn("ux_domWaitForConnection", src)
        self.assertNotIn("document.messageHandler =", src)
        self.assertNotIn("document.waitForConnection =", src)
        self.assertIn("x-tagname", src)


class TestUxChannelRuntimeOptional(unittest.TestCase):
    def test_optional_soft(self):
        # May return instance or None depending on install; must not raise
        rt = UxChannelRuntime.optional()
        if rt is not None:
            self.assertEqual(rt.name, "ux_channel")
            self.assertFalse(rt.mount_via_ux_dom)
            # tags-only by default
            self.assertEqual(list(rt.served_files()), [])

    def test_channel_alias_is_runtime_not_action_plane(self):
        from ux_dom.runtime import Channel

        self.assertIs(Channel, UxChannelRuntime)


class TestNoLegacyScriptAliases(unittest.TestCase):
    def test_scripts_module_surface(self):
        import ux_dom.scripts as s

        self.assertTrue(hasattr(s, "x_element_js"))
        self.assertFalse(hasattr(s, "html_elements"))
        self.assertFalse(hasattr(s, "x_component_js"))


if __name__ == "__main__":
    unittest.main()
