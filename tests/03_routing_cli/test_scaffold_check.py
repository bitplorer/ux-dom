"""Product scaffold integrity lives on uxcompose — uxdom doctor teaches that."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ux_dom.cli.doctor import run_doctor
from helpers import ScaffoldOptions, create_app


class TestProductScaffoldMoved(unittest.TestCase):
    def test_cli_scaffold_raises(self):
        from ux_dom.cli import scaffold as sc

        with self.assertRaises(ImportError) as ctx:
            sc.create_app()
        self.assertIn("uxcompose create-app", str(ctx.exception))

        with self.assertRaises(ImportError):
            sc.available_templates()

        with self.assertRaises(ImportError):
            sc.ScaffoldOptions("x")

        with self.assertRaises(ImportError):
            sc.validate_scaffold(Path("."))

    def test_scaffold_check_module_gone(self):
        with self.assertRaises(ImportError):
            from ux_dom.cli.scaffold_check import assert_scaffold_ok  # noqa: F401

    def test_doctor_teaches_uxcompose(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions("doc", dest=Path(td) / "doc", force=True)
            )
            report = run_doctor(cwd=root)
            names = [c.name for c in report.checks]
            self.assertIn("product-scaffold", names)
            detail = next(c.detail for c in report.checks if c.name == "product-scaffold")
            self.assertIn("uxcompose create-app", detail)


if __name__ == "__main__":
    unittest.main()
