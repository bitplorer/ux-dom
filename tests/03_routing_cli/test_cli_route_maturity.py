"""CLI + DirectoryRoutes maturity: dynamic routes, add, build edges."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from helpers import ScaffoldOptions, create_app
from ux_dom.cli.adders import AddError, add_route, add_xelement
from ux_dom.cli.build import run_build
from ux_dom.dom import div, template
from ux_dom.dom.htmlelement import CustomElement


class TestDynamicRouteMaturity(unittest.TestCase):
    def test_users_id_route_py_component_200(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "dyn",
                    dest=Path(td) / "dyn",
                    force=True,
                    with_tailwind=False,
                )
            )
            old = Path.cwd()
            try:
                os.chdir(root)
                p = add_route("users/[id]", force=True)
                self.assertTrue(p.name == "route.py")
                self.assertTrue((root / "app/routes/users/__init__.py").is_file())
                self.assertIn("id: str", p.read_text())
                self.assertNotIn("**path_params", p.read_text())

                sys.path.insert(0, str(root))
                for k in list(sys.modules):
                    if k == "app" or k.startswith("app."):
                        del sys.modules[k]
                from app.main import app

                c = TestClient(app)
                self.assertEqual(c.get("/").status_code, 200)
                r = c.get("/users/42")
                self.assertEqual(r.status_code, 200, r.text)
                self.assertIn("42", r.text)  # title f-string
            finally:
                os.chdir(old)
                for k in list(sys.modules):
                    if k == "app" or k.startswith("app."):
                        del sys.modules[k]
                if str(root) in sys.path:
                    sys.path.remove(str(root))

    def test_nested_static_route(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "n", dest=Path(td) / "n", force=True, with_tailwind=False
                )
            )
            old = Path.cwd()
            try:
                os.chdir(root)
                add_route("admin/dashboard", force=True)
                sys.path.insert(0, str(root))
                for k in list(sys.modules):
                    if k == "app" or k.startswith("app."):
                        del sys.modules[k]
                from app.main import app

                c = TestClient(app)
                r = c.get("/admin/dashboard")
                self.assertEqual(r.status_code, 200, r.text)
            finally:
                os.chdir(old)
                for k in list(sys.modules):
                    if k == "app" or k.startswith("app."):
                        del sys.modules[k]
                if str(root) in sys.path:
                    sys.path.remove(str(root))

    def test_empty_name_rejected(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "e", dest=Path(td) / "e", force=True, with_tailwind=False
                )
            )
            old = Path.cwd()
            try:
                os.chdir(root)
                with self.assertRaises(AddError):
                    add_route("")
            finally:
                os.chdir(old)


class TestXElementAlpineGenerated(unittest.TestCase):
    def test_alpine_stub_imports(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "x", dest=Path(td) / "x", force=True, with_tailwind=False
                )
            )
            old = Path.cwd()
            try:
                os.chdir(root)
                p = add_xelement("Toggle", kind="alpine", force=True)
                # syntax-check generated file
                compile(p.read_text(encoding="utf-8"), str(p), "exec")
            finally:
                os.chdir(old)


class TestBuildDeployHardening(unittest.TestCase):
    def test_build_ok_without_tailwind(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "b",
                    dest=Path(td) / "b",
                    force=True,
                    with_tailwind=False,
                )
            )
            rep = run_build(cwd=root)
            self.assertTrue(rep.ok, rep.steps)


class TestBooleanShadowNotEmitted(unittest.TestCase):
    def test_custom_element_shadowroot_true_string(self):
        class H(CustomElement):
            def render(self, tag_name="h"):
                return template(div("x"), **{"x-tagname": tag_name})

        html = str(H("h"))
        self.assertNotIn('shadowdom="shadowdom"', html)


def _drop_app_modules() -> None:
    for k in [k for k in sys.modules if k == "app" or k.startswith("app.")]:
        del sys.modules[k]


class TestAddRouteGeneratesLawfulFiles(unittest.TestCase):
    """``uxdom add route`` output must import and route under DirectoryRouter."""

    def _app(self, td, *names, methods="get"):
        root = create_app(
            ScaffoldOptions(
                "g", dest=Path(td) / "g", force=True, with_tailwind=False
            )
        )
        for n in names:
            add_route(n, root=root, force=True, methods=methods)
        sys.path.insert(0, str(root))
        self.addCleanup(sys.path.remove, str(root))
        _drop_app_modules()
        self.addCleanup(_drop_app_modules)
        from app.main import app

        return TestClient(app)

    def test_static_param_and_snake_routes(self):
        with TemporaryDirectory() as td:
            c = self._app(td, "my-page", "orgs/[org]/teams/[team]", "admin/dashboard")
            self.assertEqual(c.get("/my_page").status_code, 200)
            r = c.get("/orgs/acme/teams/core")
            self.assertEqual(r.status_code, 200, r.text)
            self.assertIn("acme", r.text)
            self.assertIn("core", r.text)
            self.assertEqual(c.get("/admin/dashboard").status_code, 200)

    def test_methods_option_adds_verbs(self):
        with TemporaryDirectory() as td:
            c = self._app(td, "notes", "items/[id]", methods="get,post")
            self.assertEqual(c.post("/notes").status_code, 200)
            self.assertEqual(c.post("/items/7").status_code, 200)

    def test_cli_add_route_runs(self):
        from typer.testing import CliRunner

        from ux_dom.cli.cli import app as cli

        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "h", dest=Path(td) / "h", force=True, with_tailwind=False
                )
            )
            old = Path.cwd()
            os.chdir(root)
            try:
                r = CliRunner().invoke(
                    cli, ["add", "route", "about2", "--methods", "get,post"]
                )
            finally:
                os.chdir(old)
            self.assertEqual(r.exit_code, 0, f"{r.stdout!r} {r.exception!r}")
            self.assertTrue((root / "app/routes/about2.py").is_file())
