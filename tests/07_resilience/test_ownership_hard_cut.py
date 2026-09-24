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
            "ux_dom.cli.scaffold",
            "ux_dom.cli.tailwind",
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
    def test_cli_scaffold_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.cli.scaffold  # noqa: F401

    def test_create_project_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.create  # noqa: F401
        with self.assertRaises(ImportError):
            import ux_dom.create.project  # noqa: F401


class TestDirectoryRoutesTeaching(unittest.TestCase):
    def test_routing_core_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.routing.core  # noqa: F401
        with self.assertRaises(ImportError):
            import ux_dom.routing.facade  # noqa: F401

    def test_fastapi_host_module_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.plugins.host  # noqa: F401

    def test_hotreload_plugin_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.plugins.hmr  # noqa: F401

    def test_leftover_directory_router_still_importable(self):
        from ux_dom.routing.fastapi import DirectoryRouter, StreamingRoute

        self.assertTrue(callable(DirectoryRouter))
        self.assertTrue(callable(StreamingRoute))

    def test_app_fastapi_still_refuses(self):
        from ux_dom.plugins.hub import App, ProductHostMoved

        with self.assertRaises(ProductHostMoved) as ctx:
            App().fastapi()
        self.assertIn("ux_compose.build", str(ctx.exception))


class TestProductCssFailClosed(unittest.TestCase):
    def test_tailwind_command_is_not_public(self):
        import ux_dom

        self.assertFalse(hasattr(ux_dom, "TailwindCommand"))
        with self.assertRaises(ImportError):
            import ux_dom.settings.commands  # noqa: F401

    def test_cli_tailwind_module_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.cli.tailwind  # noqa: F401

    def test_webassets_is_not_public(self):
        import ux_dom

        self.assertFalse(hasattr(ux_dom, "WebAssets"))

    def test_tailwind_style_is_absent(self):
        from ux_dom.plugins import style

        self.assertFalse(hasattr(style, "TailwindStyle"))
        self.assertEqual(style.__all__, ["NullStyle"])

    def test_document_has_no_webassets_field(self):
        from dataclasses import fields

        from ux_dom import Document

        names = {f.name for f in fields(Document)}
        self.assertNotIn("webassets", names)
        with self.assertRaises(TypeError):
            Document(head=[], webassets=object())
