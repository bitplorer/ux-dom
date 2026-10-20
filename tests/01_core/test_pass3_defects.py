"""Pass-3 audit locks (#59): textarea value, dedupe key, xelement stubs."""
from __future__ import annotations

import asyncio
import importlib.util
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ux_dom.cli.adders import add_xelement
from ux_dom.dom import div, form, link, script, textarea
from ux_dom.plugins.dedupe import dedupe_dom_nodes
from ux_dom.ui import Textarea

_VALUE = "line1\nline2"
_INNER = re.compile(r"<textarea[^>]*>(.*?)</textarea>", re.S)


def _async_html(node, pretty):
    async def run():
        return "".join([c async for c in node.__async_render__(pretty=pretty)])

    return asyncio.run(run())


class TestTextareaValue(unittest.TestCase):
    """G2: pretty indentation must not leak into the form value."""

    def _assert_value(self, node):
        for pretty in (True, False):
            for html in (node.__render__(pretty=pretty), _async_html(node, pretty)):
                with self.subTest(pretty=pretty, html=html):
                    self.assertEqual(_INNER.search(html).group(1), _VALUE)

    def test_textarea_tag(self):
        self._assert_value(form(textarea(_VALUE, name="bio")))

    def test_ui_textarea(self):
        self._assert_value(form(Textarea(_VALUE, name="bio")))


class TestDedupeKey(unittest.TestCase):
    """G3: dedupe keys on (tag, rel, url) of script/link nodes only."""

    def test_preconnect_does_not_drop_stylesheet(self):
        nodes = [
            link(rel="preconnect", href="https://cdn.x"),
            link(rel="stylesheet", href="https://cdn.x"),
        ]
        self.assertEqual(len(dedupe_dom_nodes(nodes)), 2)

    def test_wrapper_is_not_keyed_as_its_script(self):
        nodes = [div(script(src="/a.js")), script(src="/a.js")]
        self.assertEqual(len(dedupe_dom_nodes(nodes)), 2)

    def test_same_link_still_deduped(self):
        nodes = [
            link(rel="stylesheet", href="/s.css"),
            link(rel="stylesheet", href="/s.css"),
        ]
        self.assertEqual(len(dedupe_dom_nodes(nodes)), 1)

    def test_rel_token_order_ignored(self):
        nodes = [
            link(rel="stylesheet preload", href="/s.css"),
            link(rel="preload  stylesheet", href="/s.css"),
        ]
        self.assertEqual(len(dedupe_dom_nodes(nodes)), 1)
        raw = [
            '<link rel="stylesheet preload" href="/s.css">',
            '<link href="/s.css" rel="Preload Stylesheet">',
        ]
        self.assertEqual(len(dedupe_dom_nodes(raw)), 1)

    def test_preload_link_keeps_script(self):
        nodes = [link(rel="preload", href="/x.js", _as="script"), script(src="/x.js")]
        self.assertEqual(len(dedupe_dom_nodes(nodes)), 2)

    def test_raw_string_ignores_data_attrs(self):
        # data-src is not a resource URL: the two scripts load different files
        raw = [
            '<script data-src="/a.js" src="/b.js"></script>',
            '<script src="/a.js"></script>',
        ]
        self.assertEqual(len(dedupe_dom_nodes(raw)), 2)
        # a data-href-only link loads nothing, so it is never keyed
        lazy = ['<link data-href="/s.css">', '<link data-href="/s.css">']
        self.assertEqual(len(dedupe_dom_nodes(lazy)), 2)


class TestAddXElementStubs(unittest.TestCase):
    """G4: every ``uxdom add xelement`` variant constructs and renders."""

    def test_variants_construct_and_render(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "app" / "routes").mkdir(parents=True)
            for kind in ("light", "shadow", "alpine"):
                with self.subTest(kind=kind):
                    name = f"pass3-stub-{kind}"
                    path = add_xelement(name, kind=kind, root=root)
                    spec = importlib.util.spec_from_file_location(
                        f"_pass3_{kind}", path
                    )
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    cls = next(
                        v
                        for v in vars(mod).values()
                        if isinstance(v, type) and v.__module__ == mod.__name__
                    )
                    host = str(cls())
                    self.assertIn(f"<x-{name}", host)
                    definition = str(cls.definition())
                    self.assertIn(f'x-tagname="{name}"', definition)


if __name__ == "__main__":
    unittest.main()
