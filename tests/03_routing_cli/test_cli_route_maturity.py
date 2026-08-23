"""CLI + DirectoryRouter maturity: dynamic routes, add, build, deploy edges."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from ux_dom.cli.adders import AddError, add_route, add_xelement
from ux_dom.cli.build import run_build
try:
    from ux_dom.cli.deploy import prepare_deploy
except ImportError:  # product deploy lives on uxcompose
    prepare_deploy = None


def _require_deploy():
    if prepare_deploy is None:
        raise unittest.SkipTest("product deploy is uxcompose, not uxdom")
from helpers import ScaffoldOptions, create_app
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
                self.assertEqual(c.get("/index").status_code, 200)
                r = c.get("/users/42/Page")
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
                r = c.get("/admin/dashboard/Dashboard")
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
            rep = run_build(cwd=root, skip_tailwind=True)
            self.assertTrue(rep.ok, rep.steps)

    def test_deploy_dockerfile_uses_port_env(self):
        _require_deploy()
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "d", dest=Path(td) / "d", force=True, with_tailwind=False
                )
            )
            prepare_deploy("docker", cwd=root, force=True)
            df = (root / "Dockerfile").read_text()
            self.assertIn("${PORT:-8080}", df)
            self.assertNotIn("skip tw", df)


class TestBooleanShadowNotEmitted(unittest.TestCase):
    def test_custom_element_shadowroot_true_string(self):
        class H(CustomElement):
            def render(self, tag_name="h"):
                return template(div("x"), **{"x-tagname": tag_name})

        html = str(H("h"))
        self.assertNotIn('shadowdom="shadowdom"', html)
