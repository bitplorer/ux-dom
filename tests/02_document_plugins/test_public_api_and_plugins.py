"""Public exports + plugin hub contracts."""

from __future__ import annotations

import unittest

import ux_dom
from ux_dom import (
    Component,
    Fragment,
    __version__,
)
from ux_dom.plugins import App, PluginHub, get_hub, set_hub
from ux_dom.plugins.control import ChannelControl, NullControl


class TestPublicAPI(unittest.TestCase):
    def test_version_bump_area(self):
        self.assertTrue(__version__)
        self.assertEqual(ux_dom.__version__, __version__)
        self.assertFalse(hasattr(ux_dom, "WebAssets"))
        self.assertFalse(hasattr(ux_dom, "TailwindCommand"))
        self.assertFalse(hasattr(ux_dom, "CreateProject"))

    def test_component_top_level(self):
        class Box(Component):
            def render(self, *a, **k):
                from ux_dom.dom import div

                return div("hi", id="box")

        html = Box().__render__(pretty=False)
        self.assertIn('id="box"', html)
        self.assertIn("hi", html)

    def test_fragment_export(self):
        from ux_dom.dom import div

        f = Fragment(div("a"), div("b"))
        html = f.__render__(pretty=False)
        self.assertIn(">a<", html)
        self.assertIn(">b<", html)


class TestPluginHub(unittest.TestCase):
    def test_hub_register_control(self):
        hub = PluginHub()
        hub.add_control(NullControl())
        hub.add_control(ChannelControl())
        self.assertIn("null", hub.controls)
        self.assertIn("channel", hub.controls)
        self.assertEqual(hub.summary()[-1], "control:channel")

    def test_app_use_null(self):
        app = App(debug=True).use(NullControl())
        self.assertEqual(list(app.plugin_summary()), ["control:null"])

    def test_get_set_hub(self):
        old = get_hub()
        h = PluginHub()
        set_hub(h)
        self.assertIs(get_hub(), h)
        set_hub(old)


class TestChannelAttrInterop(unittest.TestCase):
    """data-channel-* survives Tags dialect (channel peer control plane)."""

    def test_data_channel_attrs(self):
        from ux_dom.dom import button

        # as_ux_dom-style (ux-channel) keys
        kwargs = {
            "data_channel_action": "Save",
            "data_channel_id": "Form:root",
            "data_channel_cap": "sig",
        }
        html = button("Save", **kwargs).__render__(pretty=False)
        self.assertIn('data-channel-action="Save"', html)
        self.assertIn('data-channel-id="Form:root"', html)
        self.assertIn('data-channel-cap="sig"', html)


if __name__ == "__main__":
    unittest.main()
