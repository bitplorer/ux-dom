"""DX commands: doctor, add, lint, tutorial scaffold, diagnostics.

Product create-app / serve / deploy live on uxcompose only.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from typer.testing import CliRunner

from helpers import ScaffoldOptions, available_templates, create_app
from ux_dom.cli.adders import AddError, add_component, add_route, add_xelement
from ux_dom.cli.cli import app as cli_app
from ux_dom.cli.doctor import run_doctor
from ux_dom.cli.lint import lint_project

ROOT = Path(__file__).resolve().parents[2]


class TestDoctor(unittest.TestCase):
    def test_doctor_on_empty_dir(self):
        with TemporaryDirectory() as td:
            rep = run_doctor(cwd=Path(td))
            self.assertIsNotNone(rep)
            names = {c.name for c in rep.checks}
            self.assertIn("python", names)

    def test_doctor_on_scaffold(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "d", dest=Path(td) / "d", force=True, with_tailwind=False
                )
            )
            rep = run_doctor(cwd=root)
            names = {c.name for c in rep.checks}
            self.assertIn("project", names)


class TestAddCommands(unittest.TestCase):
    def test_add_component(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "a", dest=Path(td) / "a", force=True, with_tailwind=False
                )
            )
            old = Path.cwd()
            try:
                os.chdir(root)
                p = add_component("Widget", force=True)
                self.assertTrue(p.is_file())
                self.assertIn("class Widget", p.read_text())
            finally:
                os.chdir(old)

    def test_add_route_index(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "r", dest=Path(td) / "r", force=True, with_tailwind=False
                )
            )
            old = Path.cwd()
            try:
                os.chdir(root)
                # index already exists from scaffold; force overwrite
                p = add_route("index", force=True)
                self.assertTrue(p.is_file())
                self.assertIn('routes = ["/"]', p.read_text())
            finally:
                os.chdir(old)

    def test_add_without_force_raises(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "f", dest=Path(td) / "f", force=True, with_tailwind=False
                )
            )
            old = Path.cwd()
            try:
                os.chdir(root)
                add_component("Dup", force=True)
                with self.assertRaises(AddError):
                    add_component("Dup", force=False)
            finally:
                os.chdir(old)


class TestLint(unittest.TestCase):
    def test_lint_scaffold(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "l", dest=Path(td) / "l", force=True, with_tailwind=False
                )
            )
            issues = lint_project(root)
            # pure-dom scaffold should be clean or only soft warns
            self.assertIsInstance(issues, list)


class TestCliEntry(unittest.TestCase):
    def test_root_help(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("doctor", result.output)
        self.assertIn("add", result.output)
        self.assertNotIn("create-app", result.output)

    def test_doctor_help(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["doctor", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--path", result.output)

    def test_add_help(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["add", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)

    def test_create_app_absent(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["create-app", "x"])
        self.assertNotEqual(result.exit_code, 0)

    def test_module_entry_help(self):
        # subprocess entry preserves CLI surface
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "from ux_dom.cli import ux_dom; ux_dom(['--help'])",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT)},
            timeout=30,
        )
        out = proc.stdout + proc.stderr
        self.assertTrue(
            "doctor" in out or proc.returncode == 0,
            out[-500:],
        )
        self.assertNotIn("create-app", out)


if __name__ == "__main__":
    unittest.main()
