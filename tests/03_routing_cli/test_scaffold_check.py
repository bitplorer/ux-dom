"""Hardened create-app scaffold integrity checks."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ux_dom.cli.doctor import run_doctor
from ux_dom.cli.scaffold import ScaffoldOptions, create_app, validate_scaffold
from ux_dom.cli.scaffold_check import ScaffoldError, assert_scaffold_ok


class TestScaffoldValidate(unittest.TestCase):
    def test_fresh_minimal_ok(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions("okapp", dest=Path(td) / "okapp", force=True)
            )
            r = validate_scaffold(root, expect_template="minimal")
            self.assertTrue(r.ok, r.to_dict())

    def test_detects_missing_document(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions("miss", dest=Path(td) / "miss", force=True)
            )
            (root / "app" / "document.py").unlink()
            r = validate_scaffold(root)
            self.assertFalse(r.ok)
            codes = {i.code for i in r.errors}
            self.assertIn("missing_file", codes)

    def test_detects_placeholder_leak(self):
        with TemporaryDirectory() as td:
            root = create_app(ScaffoldOptions("ph", dest=Path(td) / "ph", force=True))
            p = root / "app" / "settings.py"
            p.write_text(p.read_text() + "\nTITLE = {{AppTitle}}\n")
            r = validate_scaffold(root)
            self.assertFalse(r.ok)
            self.assertTrue(any(i.code == "placeholder" for i in r.errors))

    def test_detects_syntax_error(self):
        with TemporaryDirectory() as td:
            root = create_app(ScaffoldOptions("syn", dest=Path(td) / "syn", force=True))
            (root / "app" / "main.py").write_text("def broken(\n")
            r = validate_scaffold(root)
            self.assertFalse(r.ok)
            self.assertTrue(any(i.code == "syntax" for i in r.errors))

    def test_csp_contract(self):
        with TemporaryDirectory() as td:
            root = create_app(ScaffoldOptions("csp", dest=Path(td) / "csp", force=True))
            doc = root / "app" / "document.py"
            # strip CSP wiring
            text = doc.read_text().replace("Csp", "NoCsp")
            doc.write_text(text)
            r = validate_scaffold(root)
            self.assertFalse(r.ok)
            self.assertTrue(any(i.code == "document_csp" for i in r.errors))

    def test_assert_raises(self):
        with TemporaryDirectory() as td:
            root = Path(td) / "empty"
            root.mkdir()
            with self.assertRaises(ScaffoldError):
                assert_scaffold_ok(root)

    def test_doctor_includes_integrity(self):
        with TemporaryDirectory() as td:
            root = create_app(ScaffoldOptions("doc", dest=Path(td) / "doc", force=True))
            report = run_doctor(cwd=root)
            names = [c.name for c in report.checks]
            self.assertTrue(any(n.startswith("scaffold:") for n in names), names)


if __name__ == "__main__":
    unittest.main()
