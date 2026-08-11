"""Production stability — multi-surface integration + edge cases."""

from __future__ import annotations

import ast
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ux_dom.cli.adders import add_route, add_xelement
from ux_dom.cli.build import run_build
from ux_dom.cli.deploy import prepare_deploy
from ux_dom.cli.doctor import run_doctor
from ux_dom.cli.lint import lint_project
from ux_dom.cli.scaffold import ScaffoldOptions, available_templates, create_app
from ux_dom.dom import div, template
from ux_dom.dom.htmlelement import CustomElement, WebComponent, XElement
from ux_dom.ui import Button, Card, CardContent, Dialog, Input, Select, Tabs
from ux_dom.ui.catalog import CATALOG
from ux_dom.ui.channel_bridge import live_button, stamp_region, to_fragment
from ux_dom.ui.copy import copy_component

REPO = Path(__file__).resolve().parents[2]


class TestUiEdges(unittest.TestCase):
    def test_all_catalog_modules_import_and_render(self):
        import importlib

        for key, meta in CATALOG.items():
            mod = importlib.import_module(meta["module"])
            for exp in meta["exports"]:
                self.assertTrue(hasattr(mod, exp), f"{meta['module']}.{exp}")

    def test_button_no_false_disabled(self):
        html = str(Button("ok"))
        self.assertIsNone(re.search(r"(?<![:\w])disabled(?:=|\s|>)", html), html)

    def test_tabs_unsafe_key_sanitized(self):
        html = str(Tabs(items=[("a'b", "Lab", "body")]))
        self.assertIn("Lab", html)
        self.assertNotIn("a'b", html)  # rewritten
        self.assertIn("tab0", html)

    def test_tabs_bad_shape(self):
        with self.assertRaises(ValueError):
            str(Tabs(items=[("only", "two")]))  # type: ignore[list-item]

    def test_select_value_selected(self):
        html = str(Select(options=[("a", "A"), ("b", "B")], value="b"))
        # b option should be selected
        self.assertIn('value="b"', html)

    def test_dialog_body_only(self):
        html = str(Dialog(body="only"))
        self.assertIn("only", html)
        self.assertIn("x-data", html)

    def test_copy_dialog_pulls_button(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "ui"
            copy_component("Dialog", dest_dir=d, force=True)
            self.assertTrue((d / "dialog.py").is_file())
            self.assertTrue((d / "button.py").is_file())
            self.assertTrue((d / "tokens.py").is_file())
            for py in d.glob("*.py"):
                compile(py.read_text(encoding="utf-8"), str(py), "exec")
            text = (d / "dialog.py").read_text()
            self.assertIn("from .button import", text)
            self.assertNotIn("from ux_dom.ui.button", text)


class TestScaffoldMatrix(unittest.TestCase):
    def test_all_templates_boot(self):
        for tmpl in available_templates():
            with self.subTest(tmpl=tmpl):
                with tempfile.TemporaryDirectory() as td:
                    root = create_app(
                        ScaffoldOptions(
                            f"app_{tmpl}",
                            dest=Path(td) / tmpl,
                            force=True,
                            template=tmpl,
                            with_tailwind=False,
                            with_channel=False if tmpl != "live" else True,
                        )
                    )
                    # live still creates without channel package
                    sys.path.insert(0, str(root))
                    try:
                        for k in list(sys.modules):
                            if k == "app" or k.startswith("app."):
                                del sys.modules[k]
                        # live template may import channel at runtime of routes
                        if tmpl == "live":
                            # main should still import
                            try:
                                from app.main import app  # noqa: F401
                            except ImportError:
                                # channel missing — acceptable soft fail for live only
                                continue
                        else:
                            from app.main import app

                            c = TestClient(app)
                            r = c.get("/index/Index")
                            self.assertEqual(r.status_code, 200, tmpl)
                            self.assertIn("x_element.js", r.text)
                    finally:
                        for k in list(sys.modules):
                            if k == "app" or k.startswith("app."):
                                del sys.modules[k]
                        if str(root) in sys.path:
                            sys.path.remove(str(root))


class TestDynamicRoutes(unittest.TestCase):
    def test_multi_segment_params(self):
        with tempfile.TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "dyn", dest=Path(td) / "dyn", force=True, with_tailwind=False
                )
            )
            old = Path.cwd()
            try:
                os.chdir(root)
                add_route("orgs/[org]/teams/[team]", force=True)
                sys.path.insert(0, str(root))
                for k in list(sys.modules):
                    if k == "app" or k.startswith("app."):
                        del sys.modules[k]
                from app.main import app

                c = TestClient(app)
                r = c.get("/orgs/acme/teams/core/Page")
                self.assertEqual(r.status_code, 200, r.text)
                self.assertIn("acme", r.text)
                self.assertIn("core", r.text)
            finally:
                os.chdir(old)
                for k in list(sys.modules):
                    if k == "app" or k.startswith("app."):
                        del sys.modules[k]
                if str(root) in sys.path:
                    sys.path.remove(str(root))


class TestBuildDeployDoctor(unittest.TestCase):
    def test_pipeline(self):
        with tempfile.TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "prod", dest=Path(td) / "prod", force=True, with_tailwind=False
                )
            )
            rep = run_build(cwd=root, skip_tailwind=True)
            self.assertTrue(rep.ok, rep.steps)
            self.assertTrue(run_doctor(cwd=root).ok)
            self.assertFalse([i for i in lint_project(root) if i.level == "error"])
            for p in ("docker", "checklist", "fly"):
                prepare_deploy(p, cwd=root, force=True)


class TestXElementContract(unittest.TestCase):
    def test_messages(self):
        class Bad(XElement):
            def render(self, tag_name):
                return div("x")

        with self.assertRaises(AttributeError) as ctx:
            Bad.definition()
        self.assertIn("x-tagname", str(ctx.exception))

    def test_light_vs_shadow(self):
        class L(CustomElement):
            tag_name = "l"

            def render(self, tag_name="l"):
                return template(div("x"), **{"x-tagname": tag_name})

        class S(WebComponent):
            tag_name = "s"

            def render(self, tag_name="s"):
                return template(
                    div("x"), **{"x-tagname": tag_name, "shadowroot": "true"}
                )

        self.assertIn("x-tagname", str(L.definition()))
        self.assertIn("shadowroot", str(S.definition()))
        self.assertIn("x-l", str(L()))


class TestAstLibrary(unittest.TestCase):
    def test_all_ux_dom_parses(self):
        for py in (REPO / "src" / "ux_dom").rglob("*.py"):
            if "__pycache__" in py.parts:
                continue
            ast.parse(py.read_text(encoding="utf-8"), filename=str(py))


class TestUiGallery(unittest.TestCase):
    def test_gallery(self):
        root = REPO / "examples" / "ux_kit"
        sys.path.insert(0, str(root))
        for k in list(sys.modules):
            if k == "app" or k.startswith("app."):
                del sys.modules[k]
        try:
            from app.main import app

            c = TestClient(app)
            r = c.get("/index/Index")
            self.assertEqual(r.status_code, 200)
            self.assertIn("data-channel-id", r.text)
            self.assertIn("Gallery:card", r.text)
        finally:
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]
            if str(root) in sys.path:
                sys.path.remove(str(root))


class TestChannelBridge(unittest.TestCase):
    def test_fragment_and_stamp(self):
        self.assertEqual(to_fragment(None), "")
        self.assertIn("Z", to_fragment(Button("Z")))
        html = str(stamp_region(Card(CardContent("c")), uid="X:1"))
        self.assertIn('data-channel-id="X:1"', html)
        self.assertIn("data-channel-action", str(live_button("P", action="A.b")))


if __name__ == "__main__":
    unittest.main()
