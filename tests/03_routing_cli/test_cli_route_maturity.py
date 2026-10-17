"""CLI maturity: uxdom add, build edges."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


from helpers import ScaffoldOptions, create_app
from ux_dom.cli.adders import AddError, add_xelement
from ux_dom.cli.build import run_build
from ux_dom.dom import div, template
from ux_dom.dom.htmlelement import CustomElement


class TestAddRejectsBadNames(unittest.TestCase):
    def test_empty_name_rejected(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "e", dest=Path(td) / "e", force=True
                )
            )
            old = Path.cwd()
            try:
                os.chdir(root)
                with self.assertRaises(AddError):
                    add_xelement("")
            finally:
                os.chdir(old)


class TestXElementAlpineGenerated(unittest.TestCase):
    def test_alpine_stub_imports(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "x", dest=Path(td) / "x", force=True
                )
            )
            old = Path.cwd()
            try:
                os.chdir(root)
                p = add_xelement("Toggle", kind="alpine", force=True)
                # syntax-check generated file
                compile(p.read_text(encoding="utf-8"), str(p), "exec")
            finally:
                os.chdir(old)


class TestBuildDeployHardening(unittest.TestCase):
    def test_build_ok_without_tailwind(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "b",
                    dest=Path(td) / "b",
                    force=True,
                )
            )
            rep = run_build(cwd=root)
            self.assertTrue(rep.ok, rep.steps)


class TestBooleanShadowNotEmitted(unittest.TestCase):
    def test_custom_element_shadowroot_true_string(self):
        class H(CustomElement):
            def render(self, tag_name="h"):
                return template(div("x"), **{"x-tagname": tag_name})

        html = str(H("h"))
        self.assertNotIn('shadowdom="shadowdom"', html)


def _drop_app_modules() -> None:
    for k in [k for k in sys.modules if k == "app" or k.startswith("app.")]:
        del sys.modules[k]
