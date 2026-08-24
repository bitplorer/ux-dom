"""OWN/REG — product lifecycle remains outside ux-dom (FLOW hard-cut)."""
from __future__ import annotations

import importlib
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from typer.testing import CliRunner

from ux_dom.cli.cli import app as cli_app


_PRODUCT = ("create-app", "serve", "dev", "start", "deploy", "templates")


class TestProductCliAbsent(unittest.TestCase):
    def test_help_excludes_product_commands(self):
        out = CliRunner().invoke(cli_app, ["--help"]).output
        for name in _PRODUCT:
            self.assertNotRegex(
                out,
                rf"(?m)^\s*{name}\b",
                msg=f"product command leaked: {name}",
            )

    def test_product_invocations_rejected(self):
        runner = CliRunner()
        for name in ("create-app", "serve", "deploy"):
            r = runner.invoke(cli_app, [name, "--help"])
            self.assertNotEqual(r.exit_code, 0, name)

    def test_deleted_product_modules_import_error(self):
        for mod in (
            "ux_dom.cli.serve",
            "ux_dom.cli.tunnel",
            "ux_dom.cli.deploy",
        ):
            with self.assertRaises(ImportError):
                importlib.import_module(mod)

    def test_help_points_product_build_at_uxcompose(self):
        out = CliRunner().invoke(cli_app, ["--help"]).output
        self.assertIn("uxcompose", out)
        self.assertIn("build", out)


class TestProductBuildRedirect(unittest.TestCase):
    def test_product_app_py_teaches_uxcompose_build(self):
        runner = CliRunner()
        with TemporaryDirectory() as td:
            (Path(td) / "app.py").write_text("# product composition root\n", encoding="utf-8")
            prev = os.getcwd()
            try:
                os.chdir(td)
                r = runner.invoke(cli_app, ["build"])
            finally:
                os.chdir(prev)
        self.assertEqual(r.exit_code, 2, r.output)
        joined = (r.output or "") + (getattr(r, "stderr", None) or "")
        self.assertIn("uxcompose build", joined)


class TestScaffoldFailClosed(unittest.TestCase):
    def test_cli_scaffold_teaches_uxcompose(self):
        import ux_dom.cli.scaffold as sc

        with self.assertRaises(ImportError) as ctx:
            sc.available_templates()
        self.assertIn("uxcompose", str(ctx.exception).lower())

    def test_create_project_write_fail_closed(self):
        from ux_dom.create.project import CreateProject, ProductScaffoldMoved

        with self.assertRaises(ProductScaffoldMoved) as ctx:
            CreateProject("x").write("/tmp/should-not-exist-uxdom-scaffold")
        self.assertIn("uxcompose", str(ctx.exception).lower())


class TestDirectoryRoutesTeaching(unittest.TestCase):
    def test_package_doc_teaches_compose_routing(self):
        from ux_dom.routing.core import DirectoryRoutes, ProductRoutingMoved

        with self.assertRaises(ProductRoutingMoved) as ctx:
            DirectoryRoutes(".")
        self.assertIn("ux_compose.routing", str(ctx.exception))

    def test_fastapi_host_teaches_compose(self):
        from ux_dom.plugins.host import FastAPIHost, ProductHostMoved

        with self.assertRaises(ProductHostMoved) as ctx:
            FastAPIHost(title="x")
        self.assertIn("ux_compose.build", str(ctx.exception))

    def test_hotreload_plugin_teaches_compose(self):
        from ux_dom.plugins.hmr import HotReload, ProductHmrMoved

        with self.assertRaises(ProductHmrMoved) as ctx:
            HotReload()
        self.assertIn("uxcompose serve --hmr", str(ctx.exception))

    def test_leftover_directory_router_still_importable(self):
        from ux_dom.routing.fastapi import DirectoryRouter, StreamingRoute

        self.assertTrue(callable(DirectoryRouter))
        self.assertTrue(callable(StreamingRoute))


class TestProductCssFailClosed(unittest.TestCase):
    def test_tailwind_command_teaches_uxcompose_build(self):
        from ux_dom import TailwindCommand
        from ux_dom.settings.commands import ProductCssMoved

        with self.assertRaises(ProductCssMoved) as ctx:
            TailwindCommand(file_path="x", webassets=None)
        self.assertIn("uxcompose build", str(ctx.exception))

    def test_cli_tailwind_module_does_not_compile(self):
        from ux_dom.cli.tailwind import discover_css_io

        with self.assertRaises(ImportError) as ctx:
            discover_css_io(".")
        self.assertIn("ux_compose.tailwind", str(ctx.exception))

    def test_webassets_teaches_compose(self):
        from ux_dom import WebAssets
        from ux_dom.settings.document import ProductAssetsMoved

        with self.assertRaises(ProductAssetsMoved) as ctx:
            WebAssets(base_dir=".")
        msg = str(ctx.exception)
        self.assertIn("ux_compose", msg)
        self.assertIn("WebAssets", msg)
        self.assertIn("x_element.js", msg)

    def test_document_has_no_webassets_field(self):
        from dataclasses import fields

        from ux_dom import Document

        names = {f.name for f in fields(Document)}
        self.assertNotIn("webassets", names)
        with self.assertRaises(TypeError):
            Document(head=[], webassets=object())
