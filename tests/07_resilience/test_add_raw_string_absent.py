"""Absence lock: ``dom_tag.add_raw_string`` is removed; ``add(raw(s))`` replaces it."""
from __future__ import annotations

import pathlib
import unittest

from ux_dom import Component
from ux_dom.dom import div, raw
from ux_dom.dom.src.dom_tag import dom_tag

ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestAddRawStringAbsent(unittest.TestCase):
    def test_method_gone(self):
        self.assertFalse(any("add_raw_string" in vars(k) for k in dom_tag.__mro__))
        self.assertFalse(any("add_raw_string" in vars(k) for k in Component.__mro__))
        self.assertFalse(any("add_raw_string" in vars(k) for k in div.__mro__))

    def test_no_reference_in_code(self):
        hits = []
        for sub in ("src", "examples", "standalone"):
            base = ROOT / sub
            if not base.is_dir():
                continue
            for p in base.rglob("*.py"):
                if "__pycache__" in p.parts:
                    continue
                if "add_raw_string" in p.read_text(encoding="utf-8", errors="ignore"):
                    hits.append(str(p.relative_to(ROOT)))
        self.assertEqual(hits, [])

    def test_replacement_add_raw(self):
        d = div()
        r = raw("<b>&amp;</b>")
        d.add(r)
        self.assertEqual(d.__render__(pretty=False), "<div><b>&amp;</b></div>")
        self.assertIs(r.parent, d)

    def test_replacement_inside_component_root(self):
        class C(Component):
            def render(self):
                return div(id="c")

        c = C()
        c.add(raw("<i>r</i>"))
        self.assertEqual(c.__render__(pretty=False), '<div id="c"><i>r</i></div>')


if __name__ == "__main__":
    unittest.main()
