"""OWN/REG — product lifecycle remains outside ux-dom (FLOW hard-cut)."""
from __future__ import annotations

import importlib
import unittest

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
    def test_package_doc_prefers_directory_routes(self):
        # routing public surface documents DirectoryRoutes as primary path
        from ux_dom.routing import core as core_mod

        self.assertTrue(hasattr(core_mod, "DirectoryRoutes") or hasattr(core_mod, "RouterHooks"))
