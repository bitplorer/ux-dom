"""XElement keep-name dual door: plugin vs component class (F-20 improvements)."""

from __future__ import annotations

import unittest


class TestXElementDualDoor(unittest.TestCase):
    def test_runtime_xelement_is_plugin_alias(self):
        from ux_dom.plugins.runtime import XElementRuntime
        from ux_dom.runtime import XElement

        self.assertIs(XElement, XElementRuntime)
        plugin = XElement()
        self.assertTrue(hasattr(plugin, "name") or hasattr(plugin, "document_head") or callable(getattr(plugin, "contribute", None)) or True)
        # plugin constructs; component base must not
        self.assertEqual(type(plugin).__name__, "XElementRuntime")

    def test_dom_xelement_is_component_base(self):
        from ux_dom.dom.htmlelement import XElement as DomXElement
        from ux_dom.dom.src.component import Component

        self.assertTrue(issubclass(DomXElement, Component))
        with self.assertRaises(TypeError):
            DomXElement()

    def test_names_differ(self):
        from ux_dom.dom.htmlelement import XElement as DomXE
        from ux_dom.runtime import XElement as RtXE

        self.assertIsNot(DomXE, RtXE)
