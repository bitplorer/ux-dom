"""Pure-dom DX residuals: Tailwind resolver + envfile + doctor.

Product lifecycle (create-app / serve / dev / start / tunnel / deploy) lives on
uxcompose only. This module locks that absence and keeps pure-dom tooling tests.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from typer.testing import CliRunner

from ux_dom.cli.cli import app as cli_app
from ux_dom.cli.envfile import env_files_for, load_env_files, parse_env_text
from ux_dom.cli.tailwind import (
    argv_with_io,
    discover_css_io,
    resolve_tailwind,
    resolve_tailwind_argv,
    standalone_asset_name,
)

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


class TestTailwindResolver(unittest.TestCase):
    def setUp(self):
        os.environ["UXDOM_TAILWIND_DOWNLOAD"] = "0"
        os.environ.pop("UXDOM_TAILWIND", None)
        os.environ.pop("TAILWINDCSS", None)

    def tearDown(self):
        os.environ.pop("UXDOM_TAILWIND", None)
        os.environ.pop("TAILWINDCSS", None)

    def test_env_wins(self):
        with TemporaryDirectory() as td:
            fake = Path(td) / "tw"
            fake.write_text("#!/bin/sh\n")
            fake.chmod(0o755)
            os.environ["UXDOM_TAILWIND"] = str(fake)
            hit = resolve_tailwind(ensure=False)
            self.assertIsNotNone(hit)
            self.assertEqual(hit.source, "env")
            self.assertEqual(hit.argv, [str(fake)])

    def test_no_npx_without_ensure(self):
        with patch("ux_dom.cli.tailwind._from_env", return_value=None), patch(
            "ux_dom.cli.tailwind._from_pytailwindcss", return_value=None
        ), patch("ux_dom.cli.tailwind._from_path", return_value=None):
            hit = resolve_tailwind(ensure=False)
            self.assertIsNone(hit)

    def test_argv_with_io_preserves(self):
        base = ["tailwindcss"]
        out = argv_with_io(base, input="in.css", output="out.css")
        self.assertEqual(out[0], "tailwindcss")
        self.assertIn("-i", out)
        self.assertIn("in.css", out)
        self.assertIn("-o", out)
        self.assertIn("out.css", out)

    def test_discover_css_io(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "app").mkdir()
            css = root / "app" / "input.css"
            css.write_text("@tailwind base;\n")
            pair = discover_css_io(root)
            self.assertIsNotNone(pair)

    def test_standalone_asset_name(self):
        name = standalone_asset_name()
        self.assertTrue(name.startswith("tailwindcss-"))


class TestEnvfile(unittest.TestCase):
    def test_parse_env_text(self):
        d = parse_env_text("FOO=bar\n# comment\nBAZ=qux\n")
        self.assertEqual(d["FOO"], "bar")
        self.assertEqual(d["BAZ"], "qux")
        self.assertNotIn("#", "".join(d.keys()))

    def test_env_files_for(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / ".env").write_text("A=1\n")
            (root / ".env.local").write_text("B=2\n")
            files = env_files_for(root)
            self.assertTrue(any(p.name == ".env" for p in files))

    def test_load_env_files(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / ".env").write_text("UXDOM_TEST_KEY=yes\n")
            load_env_files(root)
            self.assertEqual(os.environ.get("UXDOM_TEST_KEY"), "yes")
            os.environ.pop("UXDOM_TEST_KEY", None)


class TestDoctorSmoke(unittest.TestCase):
    def test_doctor_runs(self):
        from ux_dom.cli.doctor import run_doctor

        report = run_doctor()
        self.assertIsNotNone(report)
        self.assertTrue(hasattr(report, "checks"))
        names = [c.name for c in report.checks]
        self.assertIn("python", names)
        self.assertIn("ux_dom", names)


class TestCliHelpSurface(unittest.TestCase):
    def test_build_help(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["build", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--path", result.output)


if __name__ == "__main__":
    unittest.main()
