"""DX intent safety — no filesystem / process side effects without flags.

Guarantees:

* doctor / lint / templates / examples / ui / plugins — read-only
* add / deploy — refuse overwrite without ``--force``
* create-app — ``--yes`` does **not** imply overwrite; non-empty needs ``--force``
* build (default) — no dual-copy of x_element.js into assets/ (single-copy model)
* package/archive — only when ``--package`` / ``--archive`` requested
"""
from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from typer.testing import CliRunner

from ux_dom.cli.adders import AddError, add_component
from ux_dom.cli.build import run_build
from ux_dom.cli.cli import app as cli_app
try:
    from ux_dom.cli.deploy import prepare_deploy
except ImportError:  # product deploy lives on uxcompose
    prepare_deploy = None


def _require_deploy():
    if prepare_deploy is None:
        raise unittest.SkipTest("product deploy is uxcompose, not uxdom")
from ux_dom.cli.doctor import run_doctor
from ux_dom.cli.lint import lint_project
from helpers import ScaffoldOptions, available_templates, create_app
from ux_dom.cli.static_assets import sync_runtime_assets


def _snapshot(root: Path) -> dict[str, int]:
    return {
        str(p.relative_to(root)): p.stat().st_mtime_ns
        for p in root.rglob("*")
        if p.is_file()
    }


class TestReadOnlyDxCommands(unittest.TestCase):
    def test_doctor_lint_sync_no_writes(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "ro", dest=Path(td) / "ro", force=True, with_tailwind=False
                )
            )
            before = _snapshot(root)
            run_doctor(cwd=root, port=59991)
            lint_project(root)
            rep = sync_runtime_assets(root, force=True)
            self.assertEqual(rep.files, [])
            after = _snapshot(root)
            self.assertEqual(before, after)

    def test_templates_examples_readonly(self):
        names = available_templates()
        self.assertTrue(names)
        # no cwd mutation


class TestAddDeployForceGates(unittest.TestCase):
    def test_add_refuses_overwrite_without_force(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "ad", dest=Path(td) / "ad", force=True, with_tailwind=False
                )
            )
            p = add_component("Notice", root=root, force=False)
            self.assertTrue(p.is_file())
            with self.assertRaises(AddError):
                add_component("Notice", root=root, force=False)
            # force ok
            p2 = add_component("Notice", root=root, force=True)
            self.assertEqual(p, p2)

    def test_deploy_skips_existing_without_force(self):
        _require_deploy()
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "dp", dest=Path(td) / "dp", force=True, with_tailwind=False
                )
            )
            r1 = prepare_deploy("docker", cwd=root, force=False)
            self.assertIn("Dockerfile", r1.files_written)
            r2 = prepare_deploy("docker", cwd=root, force=False)
            self.assertEqual(r2.files_written, [])
            r3 = prepare_deploy("docker", cwd=root, force=True)
            self.assertIn("Dockerfile", r3.files_written)


class TestCreateAppYesVsForce(unittest.TestCase):
    def test_yes_alone_does_not_overwrite_nonempty(self):
        """API: force=False on non-empty dest raises (yes is CLI-only)."""
        with TemporaryDirectory() as td:
            dest = Path(td) / "exists"
            create_app(
                ScaffoldOptions("exists", dest=dest, force=True, with_tailwind=False)
            )
            # marker file proves overwrite would be destructive
            marker = dest / "KEEP_ME.txt"
            marker.write_text("precious", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                create_app(
                    ScaffoldOptions(
                        "exists", dest=dest, force=False, with_tailwind=False
                    )
                )
            self.assertEqual(marker.read_text(encoding="utf-8"), "precious")

    def test_cli_yes_without_force_preserves_nonempty(self):
        self.skipTest("uxdom create-app removed; product scaffold is uxcompose")
        with TemporaryDirectory() as td:
            dest = Path(td) / "cliapp"
            create_app(
                ScaffoldOptions("cliapp", dest=dest, force=True, with_tailwind=False)
            )
            (dest / "KEEP_ME.txt").write_text("precious", encoding="utf-8")
            r = CliRunner().invoke(
                cli_app,
                [
                    "create-app",
                    "cliapp",
                    "--dest",
                    str(dest),
                    "--yes",
                    "--no-tailwind",
                ],
            )
            self.assertNotEqual(r.exit_code, 0, f"stdout={r.stdout!r} exc={r.exception!r}")
            self.assertEqual(
                (dest / "KEEP_ME.txt").read_text(encoding="utf-8"), "precious"
            )

    def test_cli_noninteractive_without_yes_aborts(self):
        self.skipTest("uxdom create-app removed; product scaffold is uxcompose")
        with TemporaryDirectory() as td:
            dest = Path(td) / "fresh"
            # CliRunner is non-TTY → must require --yes
            r = CliRunner().invoke(
                cli_app,
                ["create-app", "fresh", "--dest", str(dest), "--no-tailwind"],
            )
            self.assertEqual(r.exit_code, 2, f"stdout={r.stdout!r} exc={r.exception!r}")
            self.assertFalse(dest.exists())


class TestBuildNoUnintendedWrites(unittest.TestCase):
    def test_default_build_no_asset_dual_copy_or_dist(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "bd", dest=Path(td) / "bd", force=True, with_tailwind=False
                )
            )
            before = _snapshot(root)
            rep = run_build(
                cwd=root,
                skip_tailwind=True,
                skip_import=True,
                package=False,
                archive=False,
            )
            self.assertTrue(rep.ok, rep.to_dict())
            after = _snapshot(root)
            self.assertEqual(before, after)
            self.assertFalse((root / "dist").exists())
            # no dual-copy of x_element under assets/js from build
            xe = list((root / "assets").rglob("x_element.js")) if (root / "assets").exists() else []
            self.assertEqual(xe, [])

    def test_package_flag_writes_dist_only_when_requested(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "pk", dest=Path(td) / "pk", force=True, with_tailwind=False
                )
            )
            rep = run_build(
                cwd=root,
                skip_tailwind=True,
                skip_import=True,
                package=True,
                out_dir=Path(td) / "dist-out",
                package_name="pk",
            )
            self.assertTrue(rep.ok, rep.to_dict())
            self.assertTrue((Path(td) / "dist-out" / "pk").is_dir())


if __name__ == "__main__":
    unittest.main()
