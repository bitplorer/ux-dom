"""CreateAsgi, host, and document mount paths used in production scaffolds."""
from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestCreateAsgiCoverage(unittest.TestCase):
    def test_create_package_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.create  # noqa: F401


class TestStaticArtifactAndPackageStatic(unittest.TestCase):
    def test_static_artifact_html_nodes(self):
        from ux_dom.plugins.contribution import StaticArtifact

        none_a = StaticArtifact(
            key="n",
            public_path="/x.js",
            inject="none",
        )
        self.assertIsNone(none_a.html_node())

        css = StaticArtifact(
            key="c",
            public_path="/a.css",
            tag="link",
            content_type="text/css",
        )
        self.assertIn("stylesheet", str(css.html_node()))

        js = StaticArtifact(
            key="j",
            public_path="/a.js",
            defer=True,
            async_=True,
        )
        self.assertIn("script", str(js.html_node()).lower())

    def test_static_from_package_x_element(self):
        from ux_dom.plugins.package_static import static_from_package

        # ux_dom.scripts ships x_element.js
        contrib = static_from_package(
            "ux_dom_scripts",
            "ux_dom.scripts",
            ["x_element.js"],
            resource_prefix="",
        )
        self.assertIn(
            'src="/ux-pkg/ux_dom_scripts/static/x_element.js"', contrib.scripts_html()
        )
        self.assertEqual(list(contrib.document_body()), [])


class TestResponseCoverage(unittest.TestCase):
    def test_html_response(self):
        from ux_dom.dom import div
        from ux_dom.response.starlette import HTMLResponse, html_response

        r = HTMLResponse(div("hi"))
        self.assertIn(b"hi", r.body)

        @html_response
        def ep():
            return div("x")

        out = ep()
        self.assertIsInstance(out, HTMLResponse)
        self.assertIn(b"x", out.body)

        @html_response
        def raw():
            return HTMLResponse(div("y"))

        self.assertIsInstance(raw(), HTMLResponse)

    def test_streaming_response(self):
        from ux_dom.dom import div
        from ux_dom.response.starlette import StreamingResponse

        r = StreamingResponse(div("stream-me"))
        self.assertTrue(r is not None)


class TestFastAPIHostCoverage(unittest.TestCase):
    def test_host_package_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.plugins.host  # noqa: F401
        with self.assertRaises(ImportError):
            import ux_dom.plugins.host.fastapi  # noqa: F401


class TestStyleTokensFunctional(unittest.TestCase):
    def test_tokens(self):
        from ux_dom.ui import tokens

        if hasattr(tokens, "cn"):
            s = tokens.cn("a", None, False, "b")
            self.assertIn("a", s)
            self.assertIn("b", s)


class TestDocumentAndPaths(unittest.TestCase):
    def test_using_and_mount(self):
        from ux_dom import Document
        from ux_dom import XElement

        d = Document(ensure_csrf_token=False).using(XElement())
        self.assertTrue(d.runtimes())
        d.mount(FastAPI())


class TestParseEscape(unittest.TestCase):
    def test_escape(self):
        from ux_dom.dom.src.utils.dom_util import escape

        self.assertIn("&lt;", escape("<x>", False))

    def test_tokenize_html(self):
        from ux_dom.dom.src.parse_html import Data, Tag, tokenize_html

        root = tokenize_html("<div class='a'>hi</div>")
        self.assertEqual(len(root), 1)
        div_ = root[0]
        self.assertIsInstance(div_, Tag)
        self.assertEqual(dict(div_.attrs), {"class": "a"})
        self.assertIsInstance(div_[0], Data)


class TestCLIModulesImport(unittest.TestCase):
    def test_imports(self):
        import ux_dom.cli.doctor  # noqa: F401
        import ux_dom.cli.lint  # noqa: F401
        with self.assertRaises(ImportError):
            import ux_dom.cli.scaffold  # noqa: F401


class TestReloaderSmoke(unittest.TestCase):
    def test_reloader_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.reloader  # noqa: F401


class TestContributionProtocol(unittest.TestCase):
    def test_xelement_tags_package_url(self):
        from ux_dom import XElement

        head = "".join(str(x) for x in XElement().document_head())
        self.assertIn('src="/ux-dom/static/x_element.js"', head)


if __name__ == "__main__":
    unittest.main()


class TestCreateAsgiStyleHmr(unittest.TestCase):
    def test_create_asgi_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.create.asgi  # noqa: F401


class TestHostLifespan(unittest.TestCase):
    def test_fastapi_host_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.plugins.host.fastapi  # noqa: F401

