"""Pure-dom DX residuals: doctor. Compiler is uxcompose build.

Product lifecycle (create-app / build / serve / deploy) lives on uxcompose
only. This module locks that absence and keeps pure-dom tooling tests.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from click import unstyle
from typer.testing import CliRunner

from ux_dom.cli.cli import app as cli_app

ROOT = Path(__file__).resolve().parents[2]

_PRODUCT_CMDS = ("create-app", "serve", "dev", "start", "deploy", "templates")


class TestProductCliAbsent(unittest.TestCase):
    def test_root_help_is_pure_dom_only(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        out = result.output
        for name in ("doctor", "info", "build", "lint", "profile", "add"):
            self.assertIn(name, out, out)
        # Typer lists commands as bare tokens on their own help lines;
        # also lock via registered command names when available.
        registered = {c.name for c in getattr(cli_app, "registered_commands", []) or []}
        if registered:
            for name in _PRODUCT_CMDS:
                self.assertNotIn(name, registered, registered)
        for name in _PRODUCT_CMDS:
            self.assertNotRegex(
                out,
                rf"(?m)^\s*{name}\b",
                msg=f"product command leaked into help: {name}\n{out}",
            )

    def test_product_commands_rejected(self):
        runner = CliRunner()
        for name in ("create-app", "serve", "dev", "start", "deploy"):
            result = runner.invoke(cli_app, [name, "--help"])
            self.assertNotEqual(
                result.exit_code, 0, f"{name} should not be a uxdom command"
            )

    def test_deleted_modules_gone(self):
        with self.assertRaises(ImportError):
            from ux_dom.cli.serve import ServeOptions  # noqa: F401
        with self.assertRaises(ImportError):
            from ux_dom.cli.tunnel import parse_provider  # noqa: F401
        with self.assertRaises(ImportError):
            from ux_dom.cli.deploy import prepare_deploy  # noqa: F401

    def test_product_commands_not_on_uxdom_cli(self):
        """create-app / deploy / serve belong to uxcompose, not uxdom."""
        from typer.main import get_command

        from ux_dom.cli.cli import app as cli_app

        names = set(get_command(cli_app).commands)
        self.assertTrue({"add", "build", "doctor"} <= names, names)
        self.assertFalse({"create-app", "deploy", "serve"} & names, names)


class TestCssCompilerNotOnUxDom(unittest.TestCase):
    """Compiler invocation left ux-dom. Compose owns it."""

    def test_tailwind_module_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.cli.tailwind  # noqa: F401


class TestTailwindCommandFailClosed(unittest.TestCase):
    def test_command_module_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.settings.commands  # noqa: F401

    def test_style_construct_is_absent(self):
        style_pkg = ROOT / "src" / "ux_dom" / "plugins" / "style"
        self.assertFalse(style_pkg.exists(), f"module still present: {style_pkg}")
        with self.assertRaises(ModuleNotFoundError):
            import ux_dom.plugins.style  # noqa: F401


class TestDoctorReportsProductCss(unittest.TestCase):
    def test_doctor_path_on_repo(self):
        from ux_dom.cli.doctor import run_doctor

        rep = run_doctor(cwd=ROOT)
        names = {c.name for c in rep.checks}
        self.assertIn("python", names)

    def test_doctor_cli_path_flag(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["doctor", "--path", str(ROOT)])
        self.assertIn("uxdom doctor", result.output)
        self.assertIn("uxcompose build", result.output)

    def test_doctor_path_option_in_help(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["doctor", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        # Typer forces Rich colour when GITHUB_ACTIONS/FORCE_COLOR is set, and
        # Rich styles "-" and "-path" separately, so compare the plain text.
        self.assertIn("--path", unstyle(result.output))


if __name__ == "__main__":
    unittest.main()
