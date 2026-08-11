"""Golden attribute dialect matrix — L0 dom_tag / L1 Tags / L2 StyleTags."""

from __future__ import annotations

import unittest

from ux_dom.dom.src.dom_tag import dom_tag
from ux_dom.dom.src.ext import StyleTags, Tags
from ux_dom.dom import div


class TestAttrDialects(unittest.TestCase):
    """Layered clean_attribute is a design feature — lock each domain."""

    def test_l0_dom_tag_baseline(self):
        self.assertEqual(dom_tag.clean_attribute("className"), "class")
        self.assertEqual(dom_tag.clean_attribute("cls"), "class")
        self.assertEqual(dom_tag.clean_attribute("htmlFor"), "for")
        self.assertEqual(dom_tag.clean_attribute("data_channel_id"), "data-channel-id")
        self.assertEqual(dom_tag.clean_attribute("aria_label"), "aria-label")
        # L0 does NOT map Alpine/HTMX
        self.assertEqual(dom_tag.clean_attribute("x_on_click"), "x_on_click")
        self.assertEqual(dom_tag.clean_attribute("hx_get"), "hx_get")

    def test_l1_tags_hypermedia(self):
        self.assertEqual(Tags.clean_attribute("className"), "class")
        self.assertEqual(Tags.clean_attribute("x_on_click"), "@click")
        self.assertEqual(Tags.clean_attribute("hx_get"), "hx-get")
        self.assertEqual(Tags.clean_attribute("hx_on_click"), "hx-on:click")
        self.assertNotEqual(Tags.clean_attribute("hx_on_click"), "h@click")
        self.assertEqual(Tags.clean_attribute("x_bind_type"), ":type")
        self.assertEqual(
            Tags.clean_attribute(
                "x_on_keydown_dot_escape_dot_prevent_dot_stop_dot_window"
            ),
            "@keydown.escape.prevent.stop.window",
        )
        self.assertEqual(
            Tags.clean_attribute("x_transition_enter"), "x-transition:enter"
        )
        self.assertEqual(Tags.clean_attribute("v_on_click"), "@click")
        self.assertEqual(Tags.clean_attribute("data_channel_action"), "data-channel-action")
        # CSS property names must NOT be rewritten on Tags
        self.assertEqual(Tags.clean_attribute("font_size"), "font_size")

    def test_l2_style_tags_css_properties(self):
        self.assertEqual(StyleTags.clean_attribute("font_size"), "font-size")
        self.assertEqual(
            StyleTags.clean_attribute("background_color"), "background-color"
        )
        self.assertEqual(StyleTags.clean_attribute("className"), "class")
        # Style dialect must NOT apply Alpine @ rewrite
        self.assertEqual(StyleTags.clean_attribute("x_on_click"), "x-on-click")

    def test_div_uses_l1(self):
        self.assertIs(div.clean_attribute.__func__, Tags.clean_attribute.__func__)
        el = div(className="a b", hx_get="/x", x_on_click="f()", data_channel_id="R1")
        html = el.__render__(pretty=False)
        self.assertIn('class="a b"', html)
        self.assertIn('hx-get="/x"', html)
        self.assertIn('@click="f()"', html)
        self.assertIn('data-channel-id="R1"', html)

    def test_multiline_class_collapse(self):
        el = div(className="""
            flex
            items-center
            """)
        html = el.__render__(pretty=False)
        self.assertIn('class="flex items-center"', html)

    def test_bool_and_none_attrs(self):
        html = div(disabled=True, hidden=False, open=None).__render__(pretty=False)
        self.assertIn('disabled="disabled"', html)
        self.assertNotIn("hidden", html)
        self.assertIn("open", html)

    def test_dict_attrs_json(self):
        html = div(x_data={"open": True}).__render__(pretty=False)
        self.assertIn("x-data=", html)
        self.assertIn("open", html)


if __name__ == "__main__":
    unittest.main()
