"""Pure-dom DX residuals: envfile + doctor. Compiler is uxcompose build.

Product lifecycle (create-app / build / serve / deploy) lives on uxcompose
only. This module locks that absence and keeps pure-dom tooling tests.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from typer.testing import CliRunner

from ux_dom.cli.cli import app as cli_app
from ux_dom.cli.envfile import env_files_for, load_env_files, parse_env_text

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


class TestCssCompilerNotOnUxDom(unittest.TestCase):
    """Compiler invocation left ux-dom. Compose owns it."""

    def test_tailwind_module_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.cli.tailwind  # noqa: F401


class TestEnvFiles(unittest.TestCase):
    def test_parse_and_load_does_not_clobber(self):
        parsed = parse_env_text(
            '# c\nexport FOO=bar\nQUOTED="x y"\nEMPTY=\nNOPE\n=bad\n'
        )
        self.assertEqual(parsed["FOO"], "bar")
        self.assertEqual(parsed["QUOTED"], "x y")
        self.assertEqual(parsed["EMPTY"], "")
        self.assertNotIn("NOPE", parsed)

        with TemporaryDirectory() as td:
            root = Path(td)
            (root / ".env").write_text("A=from-env\nB=env\n")
            (root / ".env.local").write_text("B=local\nC=local\n")
            (root / ".env.development").write_text("C=dev\n")
            env = {"A": "process"}
            read = load_env_files(root, mode="dev", environ=env)
            self.assertEqual(env["A"], "process")
            self.assertEqual(env["B"], "local")
            self.assertEqual(env["C"], "dev")
            self.assertGreaterEqual(len(read), 2)

    def test_env_files_for_prod(self):
        names = [p.name for p in env_files_for(Path("/tmp"), mode="prod")]
        self.assertIn(".env.production", names)
        self.assertNotIn(".env.development", names)


class TestTailwindCommandFailClosed(unittest.TestCase):
    def test_command_module_is_absent(self):
        with self.assertRaises(ImportError):
            import ux_dom.settings.commands  # noqa: F401

    def test_style_construct_is_absent(self):
        from ux_dom.plugins import style

        self.assertFalse(hasattr(style, "TailwindStyle"))


class TestDoctorReportsProductCss(unittest.TestCase):
    def test_doctor_path_on_repo(self):
        from ux_dom.cli.doctor import run_doctor

        rep = run_doctor(cwd=ROOT, port=59990)
        names = {c.name for c in rep.checks}
        self.assertIn("tailwind", names)
        self.assertIn("python", names)
        tw = next(c for c in rep.checks if c.name == "tailwind")
        self.assertIn("uxcompose build", tw.detail)

    def test_doctor_cli_path_flag(self):
        runner = CliRunner()
        result = runner.invoke(
            cli_app, ["doctor", "--path", str(ROOT), "--port", "59989"]
        )
        self.assertIn("uxdom doctor", result.output)
        self.assertIn("tailwind", result.output)
        self.assertIn("uxcompose build", result.output)

    def test_doctor_path_option_in_help(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["doctor", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--path", result.output)


if __name__ == "__main__":
    unittest.main()
