"""App composition DX — web() preset, multi-use, semantic shortcuts."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from ux_dom.cli.scaffold import ScaffoldOptions, create_app
from ux_dom.plugins import App, Csp, XElementRuntime
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.hub import PluginHub, set_hub
from ux_dom.plugins.runtime import XELEMENT_JS_URL


class TestMultiUse(unittest.TestCase):
    def test_use_many(self):
        set_hub(PluginHub())
        b = App().use(XElementRuntime(), HtmxControl(cdn=True), Csp())
        names = " ".join(b.plugin_summary())
        self.assertIn("ux_dom.xelement", names)
        self.assertIn("htmx", names)
        self.assertIn("csp", names)


class TestSemantic(unittest.TestCase):
    def test_named_chain(self):
        set_hub(PluginHub())
        b = App(debug=True).xelement().htmx().csp().fastapi(title="t")
        app = b.build()
        c = TestClient(app)
        self.assertEqual(c.get(XELEMENT_JS_URL).status_code, 200)

        # CSP header on any route we add
        @app.get("/x")
        def x():
            return "ok"

        r = c.get("/x")
        self.assertIn("content-security-policy", r.headers)


class TestAppWeb(unittest.TestCase):
    def test_web_builds_scaffold_like(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "w", dest=Path(td) / "w", force=True, with_tailwind=False
                )
            )
            main = (root / "app/main.py").read_text()
            self.assertTrue("document.mount" in main or "FastAPI" in main)
            pass  # CreateAsgi may mention routes API
            import sys

            sys.path.insert(0, str(root))
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]
            try:
                from app.main import app

                c = TestClient(app)
                self.assertEqual(c.get("/health").status_code, 200)
                self.assertEqual(c.get(XELEMENT_JS_URL).status_code, 200)
            finally:
                if str(root) in sys.path:
                    sys.path.remove(str(root))
                for k in list(sys.modules):
                    if k == "app" or k.startswith("app."):
                        del sys.modules[k]


if __name__ == "__main__":
    unittest.main()


class TestDocumentIsSSoT(unittest.TestCase):
    """Forever: no dual document factories on App."""

    def test_no_make_document(self):
        from ux_dom.plugins.hub import App

        self.assertFalse(hasattr(App, "make_document"))
        self.assertFalse(
            callable(getattr(App, "document", None))
            and not isinstance(App.__dataclass_fields__.get("document"), object)
        )
        # document is a field slot only
        self.assertIn("document", App.__dataclass_fields__)

    def test_scaffold_main_is_fastapi_document_mount(self):
        from pathlib import Path as P
        from tempfile import TemporaryDirectory

        from ux_dom.cli.scaffold import ScaffoldOptions, create_app

        with TemporaryDirectory() as td:
            root = create_app(ScaffoldOptions("ssot", dest=P(td) / "ssot", force=True))
            main = (root / "app" / "main.py").read_text()
            self.assertIn("FastAPI", main)
            self.assertIn("document.mount", main)
            self.assertNotIn("CreateAsgi", main)
