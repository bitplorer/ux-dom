"""Locking tests for UI kit defects D2-D5 (audit #59)."""

from __future__ import annotations

import importlib
import re
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ux_dom.dom import div
from ux_dom.ui import Breadcrumb, Chart, DropdownMenu, FormSection, Progress, Tabs
from ux_dom.ui.catalog import CATALOG
from ux_dom.ui.channel_bridge import public_form
from ux_dom.ui.copy import copy_component

_BARE_CLASS = re.compile(r"\sclass(?=[\s>/])")


class TestCopyEveryComponent(unittest.TestCase):
    def test_every_copied_module_imports(self):
        # Each component goes into its own fresh package, so a missing
        # dependency cannot be masked by another component's copy.
        for i, key in enumerate(CATALOG):
            pkg = f"_uxdom_copied_ui_{i}"
            with self.subTest(component=key), TemporaryDirectory() as td:
                copy_component(key, dest_dir=Path(td) / pkg)
                sys.path.insert(0, td)
                try:
                    importlib.import_module(f"{pkg}.{key}")
                finally:
                    sys.path.remove(td)
                    for name in [m for m in sys.modules if m.split(".")[0] == pkg]:
                        del sys.modules[name]

    def test_status_strip_copy_brings_badge(self):
        with TemporaryDirectory() as td:
            dest = Path(td) / "ui"
            copy_component("status_strip", dest_dir=dest)
            self.assertTrue((dest / "badge.py").is_file())


class TestNoBareClassAttribute(unittest.TestCase):
    def test_no_bare_class_without_classname(self):
        cases = {
            "tabs": Tabs(items=[("a", "Alpha", "body")]),
            "breadcrumb": Breadcrumb(items=[("Home", "/")]),
            "form_section": FormSection(div("x"), title="T"),
            "public_form": public_form(action="demo.save"),
        }
        for name, node in cases.items():
            with self.subTest(component=name):
                html = str(node)
                self.assertIsNone(_BARE_CLASS.search(html), html)

    def test_classname_still_applied(self):
        html = str(Breadcrumb(items=[("Home", "/")], className="crumbs"))
        self.assertIn('class="crumbs"', html)


class TestChartEmptyStyle(unittest.TestCase):
    def test_empty_chart_accepts_style(self):
        html = str(Chart(series=[], style="color:red"))
        self.assertIn('data-chart="empty"', html)
        self.assertIn("color:red", html)
        self.assertIn("width:320px", html)


class TestA11yRoles(unittest.TestCase):
    def test_dropdown_menu_roles(self):
        html = str(DropdownMenu(items=["One", "Two"], open=True))
        self.assertEqual(html.count('role="menu"'), 1, html)
        self.assertRegex(html, r'<ul[^>]*role="menu"')
        self.assertEqual(html.count('role="menuitem"'), 2, html)

    def test_tabs_roles(self):
        html = str(Tabs(items=[("a", "Alpha", "A"), ("b", "Beta", "B")], active="b"))
        self.assertIn('role="tablist"', html)
        self.assertEqual(len(re.findall(r'<button[^>]*role="tab"', html)), 2, html)

    def test_progress_clamps_aria_valuenow(self):
        over = str(Progress(value=150, max=100))
        self.assertIn('aria-valuenow="100"', over)
        under = str(Progress(value=-5, max=100))
        self.assertIn('aria-valuenow="0"', under)
        inside = str(Progress(value=40, max=100))
        self.assertIn('aria-valuenow="40"', inside)


if __name__ == "__main__":
    unittest.main()
