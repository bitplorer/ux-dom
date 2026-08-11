"""document.use (shared) vs document.using / use= (page-local)."""

from __future__ import annotations

import unittest

from ux_dom import Document
from ux_dom.dom import div, meta, title
from ux_dom.runtime import Htmx, XElement, XELEMENT_JS_URL


class TestInstanceUse(unittest.TestCase):
    def test_use_is_instance_not_class(self):
        self.assertTrue(callable(Document().use))
        self.assertFalse(isinstance(getattr(Document, "use", None), classmethod))

    def test_shared_use_mutates(self):
        doc = Document(head=[meta(charset="utf-8")])
        doc.use(XElement())
        self.assertEqual(len(doc.runtimes()), 1)
        html = str(doc(div("a")))
        self.assertIn(XELEMENT_JS_URL, html)

    def test_using_does_not_mutate_shared(self):
        base = Document(head=[meta(charset="utf-8")]).use(XElement())
        page = base.using(Htmx(cdn=True, version="2.0.4"))
        self.assertEqual(len(base.runtimes()), 1)
        self.assertEqual(len(page.runtimes()), 2)
        html_base = str(base(div("b")))
        html_page = str(page(div("p"), head=[title("P")]))
        self.assertNotIn("htmx.org", html_base)
        self.assertIn("htmx.org", html_page)
        self.assertIn(XELEMENT_JS_URL, html_page)

    def test_call_use_kwarg_page_local(self):
        base = Document(head=[meta(charset="utf-8")]).use(XElement())
        html = str(base(div("c"), use=[Htmx(cdn=True, version="2.0.4")]))
        self.assertIn("htmx.org", html)
        # base unchanged
        self.assertEqual(len(base.runtimes()), 1)
        self.assertNotIn("htmx.org", str(base(div("d"))))


if __name__ == "__main__":
    unittest.main()
