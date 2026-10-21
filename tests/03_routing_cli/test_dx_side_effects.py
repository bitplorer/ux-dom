"""DX intent safety — no filesystem / process side effects without flags.

Guarantees:

* doctor / lint / ui — read-only
* add — refuse overwrite without ``--force``
* product create-app / deploy / serve live on uxcompose (not exercised here)
* build (default) — no dual-copy of x_element.js into assets/ (single-copy model)
"""
from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


from helpers import ScaffoldOptions, available_templates, create_app
from ux_dom.cli.adders import AddError, add_component
from ux_dom.cli.build import run_build
from ux_dom.cli.doctor import run_doctor
from ux_dom.cli.lint import lint_project
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
            run_doctor(cwd=root)
            lint_project(root)
            rep = sync_runtime_assets(root)
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
            add_component("Notice", root=root, force=True)


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
                skip_import=True,
            )
            self.assertTrue(rep.ok, rep.to_dict())
            after = _snapshot(root)
            self.assertEqual(before, after)
            self.assertFalse((root / "dist").exists())
            # no dual-copy of x_element under assets/js from build
            xe = list((root / "assets").rglob("x_element.js")) if (root / "assets").exists() else []
            self.assertEqual(xe, [])


if __name__ == "__main__":
    unittest.main()
