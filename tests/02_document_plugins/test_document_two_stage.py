"""Document two-stage head/body order + callables."""

from __future__ import annotations

import unittest

from ux_dom import Document
from ux_dom.dom import div, meta, script, title
from ux_dom.plugins.csp import reset_nonce, set_nonce
from ux_dom.runtime import Htmx, XElement, XELEMENT_JS_URL


class TestTwoStageOrder(unittest.TestCase):
    def test_call_head_before_common_head(self):
        doc = Document(head=[meta(charset="utf-8")]).use(XElement())
        tree = doc(div("hi"), head=[title("PageTitle")])
        html = str(tree)
        i_title = html.find("PageTitle")
        i_charset = html.find("charset")
        i_xel = html.find(XELEMENT_JS_URL)
        self.assertGreater(i_title, 0)
        # call-time title before common charset/xelement in head
        self.assertLess(i_title, i_charset)
        self.assertLess(i_title, i_xel)

    def test_common_body_after_content(self):
        doc = Document(body=[]).use(Htmx(cdn=True, version="2.0.4"))
        tree = doc(div(id="content", **{"data-marker": "1"}))
        html = str(tree)
        i_content = html.find('id="content"')
        i_htmx = html.find("htmx.org")
        self.assertGreater(i_content, 0)
        self.assertGreater(i_htmx, i_content)

    def test_callable_in_common_head_gets_nonce(self):
        doc = Document(
            head=[
                lambda ctx: (
                    meta(name="x-nonce", content=ctx["nonce"])
                    if ctx.get("nonce")
                    else None
                )
            ]
        )
        tok = set_nonce("n-abc")
        try:
            html = str(doc(div("x")))
            self.assertIn('content="n-abc"', html)
            self.assertIn('name="x-nonce"', html)
        finally:
            reset_nonce(tok)

    def test_callable_in_call_head(self):
        doc = Document(head=[meta(charset="utf-8")])
        html = str(
            doc(
                div("z"),
                head=[lambda ctx: title(f"n={ctx.get('nonce') or 'none'}")],
            )
        )
        self.assertIn("n=none", html)


if __name__ == "__main__":
    unittest.main()
