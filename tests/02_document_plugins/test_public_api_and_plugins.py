"""Public exports + plugin hub contracts."""

from __future__ import annotations

import unittest

import ux_dom
from ux_dom import (
    Component,
    Document,
    Fragment,
    ReactiveComponent,
    WebAssets,
    __version__,
)
from ux_dom.plugins import App, PluginHub, get_hub, set_hub
from ux_dom.plugins.control import HtmxControl, NullControl
from ux_dom.plugins.routing import DirectoryRouting


class TestPublicAPI(unittest.TestCase):
    def test_version_bump_area(self):
        self.assertTrue(__version__)
        self.assertEqual(ux_dom.__version__, __version__)
        self.assertTrue(callable(WebAssets))  # fail-closed stub; still public

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
        hub.add_control(HtmxControl(cdn=False))
        self.assertIn("null", hub.controls)
        self.assertIn("htmx", hub.controls)
        self.assertEqual(hub.summary()[-1], "control:htmx")

    def test_htmx_partial_policy(self):
        ctl = HtmxControl()

        class Req:
            headers = {"hx-request": "true"}

        self.assertEqual(ctl.partial_policy(Req()), "partial")

        class Req2:
            headers = {}

        self.assertEqual(ctl.partial_policy(Req2()), "full")

    def test_htmx_body_scripts(self):
        body = HtmxControl(idiomorph=True).document_body()
        self.assertTrue(len(body) >= 1)
        rendered = "".join(str(x) for x in body)
        self.assertIn("htmx.org", rendered)

    def test_app_use_null(self):
        app = App(debug=True).use(NullControl())
        self.assertEqual(list(app.plugin_summary()), ["control:null"])

    def test_directory_routing_plugin_importable(self):
        # Don't scan filesystem here — just construct
        r = DirectoryRouting(base_directory="app", prefix="/v1")
        self.assertEqual(r.name, "directory")
        self.assertEqual(r.base_directory, "app")

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
