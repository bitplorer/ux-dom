"""Live Chromium: SVG and void elements build the tree the model has (#87).

Every element in the SVG registry is rendered empty and with a child, each
followed by a sibling, inside ``<svg>`` and inside ``<svg>`` in a ``<div>``
with an HTML sibling. Namespaces come from the model
(``htmltags._parsed_namespace``): below ``desc`` / ``title`` they are HTML. Every HTML void element, and the non-void ``param`` /
``keygen`` / ``command``, is rendered followed by a sibling. Chromium parses
each render; its element tree (``localName``, ``namespaceURI``, parent and
child order) must be the ux-dom tree, so a bare start tag that swallows its
siblings fails. Exact strings: ``tests/07_resilience/test_single_tag_registry.py``.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from ux_dom.dom import colgroup, div, span, table
from ux_dom.dom.src import htmltags, svgtags
from ux_dom.dom.src.ext import Tags

from browser_gate import NODE, require_browser

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "dom_tree_harness.mjs"

HTML_NS = "http://www.w3.org/1999/xhtml"
SVG_NS = "http://www.w3.org/2000/svg"
NS = {"html": HTML_NS, "svg": SVG_NS}

RENDERS = {
    "flat": lambda node: node.__render__(pretty=False),
    "pretty": lambda node: node.__render__(pretty=True),
}


def _svg_shapes(el):
    svg, g, rect = svgtags.svg, svgtags.g, svgtags.rect
    return {
        "empty": lambda: svg(el(), rect()),
        "child": lambda: svg(el(g()), rect()),
        "nested": lambda: svg(g(el(), el(g())), rect()),
        "in div": lambda: div(svg(el(), el(g()), rect()), span()),
    }


def _html_shapes(el):
    if el is htmltags.col:  # a <col> outside a table is dropped by the parser
        return {"empty": lambda: div(table(colgroup(el(), el())), span())}
    # ``param`` / ``keygen`` / ``command`` have end tags but the parser
    # treats them as void, so a child there is not representable.
    return {"empty": lambda: div(el(), span())}


def _model(node):
    """The element tree the ux-dom node describes, as the harness writes it."""
    out = []
    for child in node.children:
        if isinstance(child, Tags):
            name = child._clean_name(child._tagname())
            ns = NS[htmltags._parsed_namespace(child)]
            out.append([name, ns, _model(child)])
    return out


def _cases():
    elements = [getattr(svgtags, n) for n in svgtags.__all__]
    html = [
        cls
        for n in htmltags.__all__
        if isinstance(cls := getattr(htmltags, n), type)
        and issubclass(cls, htmltags.html_tag)
        and (cls.is_single or n in ("param", "keygen", "command"))
    ]
    shapes = [
        (el.__name__, shape, build)
        for el in elements
        for shape, build in _svg_shapes(el).items()
    ] + [
        (el.__name__, shape, build)
        for el in dict.fromkeys(html)
        for shape, build in _html_shapes(el).items()
    ]
    cases = []
    for name, shape, build in shapes:
        root = build()
        for mode, render in RENDERS.items():
            cases.append((name, shape, mode, render(root), _model(div(root))))
    return cases


def _browser(snippets):
    require_browser()
    proc = subprocess.run(
        [NODE, str(HARNESS)],
        cwd=str(ROOT),
        input=json.dumps(snippets),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return dict(zip(snippets, json.loads(proc.stdout)))


class TestSvgTreeBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _cases()
        cls.dom = _browser(sorted({case[3] for case in cls.cases}))

    def test_chromium_builds_the_model_tree(self):
        for name, shape, mode, html, model in self.cases:
            with self.subTest(element=name, shape=shape, render=mode):
                self.assertEqual(self.dom[html], model, html)

    def test_every_svg_element_is_covered(self):
        covered = {case[0] for case in self.cases}
        self.assertLessEqual(set(svgtags.__all__), covered)

    def test_oracle_sees_a_bare_foreign_start_tag_swallow(self):
        # Guard the oracle: a bare SVG start tag holds the sibling after it.
        dom = _browser(["<svg><animateTransform><rect></rect></svg>"])
        (tree,) = dom.values()
        self.assertEqual(
            tree,
            [["svg", SVG_NS, [["animateTransform", SVG_NS, [["rect", SVG_NS, []]]]]]],
        )


if __name__ == "__main__":
    unittest.main()
