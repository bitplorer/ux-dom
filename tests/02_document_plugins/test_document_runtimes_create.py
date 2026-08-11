"""Document.use + FastAPI/document.mount — primary composition path."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from ux_dom import Document
from ux_dom.create import CreateAsgi, CreateProject
from ux_dom.dom import meta, title
from ux_dom.runtime import Csp, Htmx, XElement, XELEMENT_JS_URL


class TestDocumentUse(unittest.TestCase):
    def test_placement_and_dedupe_name(self):
        doc = Document(head=[meta(charset="utf-8")]).use(XElement(), Htmx(cdn=True))
        h, b = doc.runtime_tags()
        self.assertTrue(any(XELEMENT_JS_URL in str(x) for x in h))
        self.assertTrue(any("htmx" in str(x) for x in b))
        doc.use(XElement())  # replace same name
        self.assertEqual(
            sum(1 for r in doc.runtimes() if r.name == "ux_dom.xelement"), 1
        )

    def test_rejects_garbage(self):
        with self.assertRaises(TypeError):
            Document().use(object())

    def test_mount_and_render(self):
        doc = Document(head=[title("T")]).use(
            XElement(), Htmx(cdn=True), Csp(debug_header=True)
        )
        app = CreateAsgi(title="t", document=doc, debug=True).build()

        @app.get("/p")
        def p():
            return str(doc("hi"))

        c = TestClient(app)
        r = c.get("/p")
        self.assertEqual(r.status_code, 200)
        self.assertIn(XELEMENT_JS_URL, r.text)
        self.assertIn("htmx.org", r.text)
        self.assertEqual(c.get(XELEMENT_JS_URL).status_code, 200)
        self.assertIn("content-security-policy", r.headers)


class TestCreateProject(unittest.TestCase):
    def test_writes_fastapi_document_mount_scaffold(self):
        with TemporaryDirectory() as td:
            root = (
                CreateProject("s", dest=Path(td) / "s")
                .force()
                .with_tailwind(False)
                .write()
            )
            main = (root / "app/main.py").read_text()
            doc = (root / "app/document.py").read_text()
            self.assertIn("FastAPI", main)
            self.assertIn("document.mount", main)
            self.assertNotIn("CreateAsgi", main)
            self.assertIn("XElement()", doc)
            self.assertIn(".use(", doc)
            import sys

            sys.path.insert(0, str(root))
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]
            try:
                from app.main import app
                from app.document import document

                c = TestClient(app)
                self.assertEqual(c.get("/health").status_code, 200)
                self.assertEqual(c.get(XELEMENT_JS_URL).status_code, 200)
                body = c.get("/health").json()
                self.assertIn("ux_dom.xelement", body.get("runtimes", []))
            finally:
                if str(root) in sys.path:
                    sys.path.remove(str(root))
                for k in list(sys.modules):
                    if k == "app" or k.startswith("app."):
                        del sys.modules[k]


if __name__ == "__main__":
    unittest.main()
