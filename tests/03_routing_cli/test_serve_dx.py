"""Next-style DX: ``uxdom serve`` / ``dev`` / ``start`` + standalone Tailwind.

Tests never download the official binary (UXDOM_TAILWIND_DOWNLOAD=0).
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from typer.testing import CliRunner

from ux_dom.cli.cli import app as cli_app
from ux_dom.cli.envfile import env_files_for, load_env_files, parse_env_text
from ux_dom.cli.serve import ServeOptions, find_app_root
from ux_dom.cli.tailwind import (
    argv_with_io,
    discover_css_io,
    resolve_tailwind,
    resolve_tailwind_argv,
    standalone_asset_name,
)

ROOT = Path(__file__).resolve().parents[2]


class TestServeHelp(unittest.TestCase):
    def test_root_help_lists_next_commands(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        out = result.output
        for name in ("create-app", "dev", "serve", "start", "doctor", "info", "build"):
            self.assertIn(name, out, out)

    def test_serve_help(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["serve", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--prod", result.output)
        self.assertIn("--no-tailwind", result.output)
        self.assertIn("--cwd", result.output)

    def test_start_help_is_prod(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["start", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("next start", result.output.lower() or result.output)

    def test_doctor_path_option(self):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["doctor", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--path", result.output)


class TestFindAppRoot(unittest.TestCase):
    def test_finds_create_app_layout(self):
        with TemporaryDirectory() as td:
            root = Path(td) / "shop"
            (root / "app").mkdir(parents=True)
            (root / "app" / "main.py").write_text("app = None\n")
            self.assertEqual(find_app_root(root / "app"), root.resolve())

    def test_missing_raises(self):
        with TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                find_app_root(Path(td))


class TestServeOptions(unittest.TestCase):
    def test_dev_reloads_by_default(self):
        opts = ServeOptions(mode="dev")
        self.assertTrue(opts.reload)
        self.assertTrue(opts.tailwind)

    def test_prod_no_reload(self):
        opts = ServeOptions(mode="prod")
        self.assertFalse(opts.reload)

    def test_bad_mode(self):
        with self.assertRaises(ValueError):
            ServeOptions(mode="staging")


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
            "ux_dom.cli.tailwind._from_path", return_value=None
        ), patch("ux_dom.cli.tailwind._from_pytailwindcss", return_value=None), patch(
            "ux_dom.cli.tailwind._from_node_modules", return_value=None
        ), patch(
            "ux_dom.cli.tailwind._cached_binary", return_value=None
        ):
            self.assertIsNone(resolve_tailwind(ensure=False))
            # ensure + download disabled → last resort npx only if present
            hit = resolve_tailwind(ensure=True)
            if hit is not None:
                self.assertEqual(hit.source, "npx")
                self.assertIn("npx", hit.argv[0])

    def test_download_disabled(self):
        os.environ["UXDOM_TAILWIND_DOWNLOAD"] = "0"
        with patch("ux_dom.cli.tailwind._from_env", return_value=None), patch(
            "ux_dom.cli.tailwind._from_path", return_value=None
        ), patch("ux_dom.cli.tailwind._from_pytailwindcss", return_value=None), patch(
            "ux_dom.cli.tailwind._from_node_modules", return_value=None
        ), patch(
            "ux_dom.cli.tailwind._cached_binary", return_value=None
        ), patch(
            "ux_dom.cli.tailwind._from_npx", return_value=None
        ), patch(
            "ux_dom.cli.tailwind.urllib.request.urlopen"
        ) as urlopen:
            self.assertIsNone(resolve_tailwind_argv(ensure=True))
            urlopen.assert_not_called()

    def test_argv_with_io_watch_vs_minify(self):
        cmd = argv_with_io(
            ["tw"],
            input_css=Path("in.css"),
            output_css=Path("out.css"),
            watch=True,
        )
        self.assertEqual(cmd[-1], "--watch")
        cmd = argv_with_io(
            ["tw"],
            input_css=Path("in.css"),
            output_css=Path("out.css"),
            minify=True,
        )
        self.assertEqual(cmd[-1], "--minify")
        self.assertNotIn("--watch", cmd)

    def test_discover_css_io(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "assets" / "css").mkdir(parents=True)
            (root / "assets" / "css" / "input.css").write_text("@import 'tailwindcss';\n")
            io = discover_css_io(root)
            self.assertIsNotNone(io)
            inp, out = io
            self.assertEqual(inp.name, "input.css")
            self.assertTrue(str(out).endswith("static/file/css/output.css"))
            self.assertTrue(out.parent.is_dir())

    def test_standalone_asset_name_linux(self):
        name = standalone_asset_name()
        self.assertTrue(name.startswith("tailwindcss-"), name)

    def test_cwd_accepts_str(self):
        with TemporaryDirectory() as td:
            os.environ["UXDOM_TAILWIND"] = str(Path(td) / "missing-bin")
            # must not raise AttributeError on str cwd
            resolve_tailwind(cwd=td, ensure=False)
            os.environ.pop("UXDOM_TAILWIND", None)


class TestEnvFiles(unittest.TestCase):
    def test_parse_and_load_does_not_clobber(self):
        parsed = parse_env_text(
            "# c\nexport FOO=bar\nQUOTED=\"x y\"\nEMPTY=\nNOPE\n=bad\n"
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
            self.assertEqual(env["A"], "process")  # process wins
            self.assertEqual(env["B"], "local")
            self.assertEqual(env["C"], "dev")
            self.assertGreaterEqual(len(read), 2)

    def test_env_files_for_prod(self):
        names = [p.name for p in env_files_for(Path("/tmp"), mode="prod")]
        self.assertIn(".env.production", names)
        self.assertNotIn(".env.development", names)


class TestTailwindCommandUsesResolver(unittest.TestCase):
    def test_tw_argv_honors_env(self):
        from ux_dom.settings.commands import TailwindCommand

        with TemporaryDirectory() as td:
            fake = Path(td) / "custom-tw"
            fake.write_text("#!/bin/sh\n")
            fake.chmod(0o755)
            os.environ["UXDOM_TAILWIND"] = str(fake)
            try:
                cmd = object.__new__(TailwindCommand)
                cmd.tailwindcss = "tailwindcss"
                cmd._root_dir = Path(td)
                self.assertEqual(cmd._tw_argv(), [str(fake)])
            finally:
                os.environ.pop("UXDOM_TAILWIND", None)

    def test_style_skips_when_cli_owns(self):
        import asyncio

        from ux_dom.plugins.style import TailwindStyle

        async def run():
            os.environ["UXDOM_TAILWIND_OWNED"] = "1"
            try:
                style = TailwindStyle(webassets=None)
                self.assertIsNone(await style.build(watch=True))
            finally:
                os.environ.pop("UXDOM_TAILWIND_OWNED", None)

        asyncio.run(run())


class TestDoctorReportsResolver(unittest.TestCase):
    def test_doctor_path_on_repo(self):
        from ux_dom.cli.doctor import run_doctor

        rep = run_doctor(cwd=ROOT, port=59990)
        names = {c.name for c in rep.checks}
        self.assertIn("tailwind", names)
        self.assertIn("python", names)

    def test_doctor_cli_path_flag(self):
        runner = CliRunner()
        result = runner.invoke(
            cli_app, ["doctor", "--path", str(ROOT), "--port", "59989"]
        )
        # python version may warn but should not hard-fail
        self.assertIn("uxdom doctor", result.output)
        self.assertIn("tailwind", result.output)


if __name__ == "__main__":
    unittest.main()
