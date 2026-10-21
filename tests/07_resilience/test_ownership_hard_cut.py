"""OWN/REG — product lifecycle remains outside ux-dom (FLOW hard-cut)."""
from __future__ import annotations

import importlib
import unittest

from typer.testing import CliRunner

from ux_dom.cli.cli import app as cli_app


_PRODUCT = ("create-app", "build", "serve", "dev", "start", "deploy", "templates")


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
        for name in ("create-app", "build", "serve", "deploy"):
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

    def test_help_points_product_lifecycle_at_uxcompose(self):
        out = CliRunner().invoke(cli_app, ["--help"]).output
        self.assertIn("Product lifecycle: uxcompose", out)


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

    def test_app_fastapi_tombstone_is_absent(self):
        import ux_dom.plugins.hub as hub

        self.assertFalse(hasattr(hub.App, "fastapi"))
        self.assertFalse(hasattr(hub, "ProductHostMoved"))

    def test_app_build_without_asgi_is_type_error(self):
        from ux_dom.plugins.hub import App

        with self.assertRaises(TypeError) as ctx:
            App().build()
        self.assertIn("asgi=", str(ctx.exception))


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
        with self.assertRaises(ImportError):
            import ux_dom.plugins.style  # noqa: F401

    def test_document_has_no_webassets_field(self):
        from dataclasses import fields

        from ux_dom import Document

        names = {f.name for f in fields(Document)}
        self.assertNotIn("webassets", names)
        with self.assertRaises(TypeError):
            Document(head=[], webassets=object())
