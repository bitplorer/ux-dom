"""Locks for extract-by-id — serialize public API (compose#80 C2).

Fragment is a tree builder. Extract slices serialized HTML.
No fragment.py. No Document / CLI / root fashion add.
No ux-channel hard dep (Soft 1/4 prefer-owner).
"""
from __future__ import annotations

import unittest
from pathlib import Path

from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "ux_dom"
SERIALIZE = SRC / "response" / "serialize.py"


class TestExtractByIdPublicSurface(unittest.TestCase):
    def test_serialize_all_names_extract_by_id(self):
        from ux_dom.response import serialize

        self.assertIn("extract_by_id", serialize.__all__)
        self.assertTrue(callable(serialize.extract_by_id))

    def test_response_all_reexports_extract_by_id(self):
        import ux_dom.response as response

        self.assertIn("extract_by_id", response.__all__)
        self.assertTrue(callable(response.extract_by_id))

    def test_not_on_package_root(self):
        import ux_dom

        self.assertFalse(hasattr(ux_dom, "extract_by_id"))

    def test_not_on_document(self):
        from ux_dom import Document

        self.assertFalse(hasattr(Document, "extract_by_id"))

    def test_uxdom_help_has_no_extract_verb(self):
        from ux_dom.cli.cli import app as cli_app

        out = CliRunner().invoke(cli_app, ["--help"]).output
        self.assertNotRegex(out, r"(?m)^\s*extract\b")


class TestExtractByIdContract(unittest.TestCase):
    def _fn(self):
        from ux_dom.response.serialize import extract_by_id

        return extract_by_id

    def test_empty_html_or_empty_id_passthrough(self):
        extract_by_id = self._fn()
        self.assertEqual(extract_by_id("", "hello"), "")
        self.assertEqual(extract_by_id("<div id='hello'></div>", ""), "<div id='hello'></div>")
        self.assertEqual(extract_by_id("<div id='hello'></div>", "#"), "<div id='hello'></div>")
        self.assertEqual(extract_by_id(None, "hello"), None)  # type: ignore[arg-type]

    def test_hash_prefix_and_bare_id_match(self):
        extract_by_id = self._fn()
        html = '<section id="shell"><p id="hello">Hi</p></section>'
        self.assertEqual(extract_by_id(html, "hello"), '<p id="hello">Hi</p>')
        self.assertEqual(extract_by_id(html, "#hello"), '<p id="hello">Hi</p>')

    def test_already_fragment_unchanged(self):
        extract_by_id = self._fn()
        html = '<div id="hello"><span>3</span></div>'
        self.assertEqual(extract_by_id(html, "hello"), html)

    def test_nested_shell_drops_outer_brand(self):
        extract_by_id = self._fn()
        html = (
            '<div id="stunning-root">'
            "<header>StunningCek</header>"
            '<span id="kernel_ssot">ssot</span>'
            '<div id="hello"><span>3</span></div>'
            "</div>"
        )
        got = extract_by_id(html, "hello")
        self.assertEqual(got, '<div id="hello"><span>3</span></div>')
        self.assertNotIn("stunning-root", got)
        self.assertNotIn("StunningCek", got)
        self.assertNotIn("kernel_ssot", got)

    def test_missing_id_leaves_html_unchanged(self):
        extract_by_id = self._fn()
        html = '<div id="shell"><p>nope</p></div>'
        self.assertEqual(extract_by_id(html, "hello"), html)

    def test_skips_comments(self):
        extract_by_id = self._fn()
        html = '<!-- <div id="hello">no</div> --><div id="hello">yes</div>'
        self.assertEqual(extract_by_id(html, "hello"), '<div id="hello">yes</div>')

    def test_void_and_self_close(self):
        extract_by_id = self._fn()
        self.assertEqual(extract_by_id('<img id="pic" src="x">tail', "pic"), '<img id="pic" src="x">')
        self.assertEqual(extract_by_id('<br id="b"/>tail', "b"), '<br id="b"/>')

    def test_quoted_id_and_id_inside_quoted_value_ignored(self):
        extract_by_id = self._fn()
        html = '<div title="id=hello"><p id="hello">ok</p></div>'
        self.assertEqual(extract_by_id(html, "hello"), '<p id="hello">ok</p>')
        html2 = "<div id='hello'>q</div>"
        self.assertEqual(extract_by_id(html2, "hello"), html2)

    def test_nested_same_name_depth(self):
        extract_by_id = self._fn()
        html = '<div id="outer"><div><div id="hello"><div>in</div></div></div></div>'
        self.assertEqual(extract_by_id(html, "hello"), '<div id="hello"><div>in</div></div>')


class TestExtractByIdKillList(unittest.TestCase):
    def test_no_fragment_py_fashion(self):
        hits = list(SRC.rglob("fragment.py"))
        self.assertEqual(hits, [], hits)

    def test_fragment_remains_tree_builder(self):
        from ux_dom import Fragment

        self.assertFalse(Fragment.render_tag)
        self.assertFalse(hasattr(Fragment, "extract_by_id"))

    def test_serialize_has_no_channel_import(self):
        text = SERIALIZE.read_text(encoding="utf-8")
        self.assertNotIn("ux_channel", text)
        self.assertNotIn("ux-channel", text)


if __name__ == "__main__":
    unittest.main()
