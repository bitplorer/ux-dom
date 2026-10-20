"""Locking tests for UI kit defects D2-D5 (audit #59)."""

from __future__ import annotations

import importlib
import re
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ux_dom.dom import a, div
from ux_dom.ui import Breadcrumb, Chart, DropdownMenu, FormSection, Progress, Tabs
from ux_dom.ui.catalog import CATALOG
from ux_dom.ui.channel_bridge import public_form
from ux_dom.ui import copy as ui_copy
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

    def test_dependency_cycle_terminates(self):
        # badge <-> button (and each importing itself) must not recurse forever
        orig = ui_copy._deps
        ui_copy._deps = lambda src: {"badge", "button"}
        try:
            for force in (False, True):
                with self.subTest(force=force), TemporaryDirectory() as td:
                    dest = Path(td) / "ui"
                    copy_component("badge", dest_dir=dest, force=force)
                    self.assertTrue((dest / "button.py").is_file())
        finally:
            ui_copy._deps = orig

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
        self.assertEqual(len(re.findall(r'<li[^>]*role="none"', html)), 2, html)
        self.assertEqual(
            len(re.findall(r'<span[^>]*role="menuitem"[^>]*tabindex="-1"', html)), 2, html
        )

    def test_dropdown_menuitem_on_focusable_child(self):
        html = str(DropdownMenu(items=[a("Edit", href="/edit")], open=True))
        self.assertRegex(html, r'<a[^>]*role="menuitem"')
        self.assertNotRegex(html, r'<li[^>]*role="menuitem"')

    def test_tabs_roles(self):
        html = str(Tabs(items=[("a", "Alpha", "A"), ("b", "Beta", "B")], active="b"))
        self.assertIn('role="tablist"', html)
        self.assertEqual(len(re.findall(r'<button[^>]*role="tab"', html)), 2, html)
        self.assertRegex(html, r'<button[^>]*aria-selected="true"[^>]*tabindex="0"')
        self.assertRegex(html, r'<button[^>]*aria-selected="false"[^>]*tabindex="-1"')
        self.assertNotIn("aria-controls", html)

    def test_tabs_aria_controls_with_id(self):
        html = str(Tabs(items=[("a", "Alpha", "A"), ("b", "Beta", "B")], active="b", id="t"))
        self.assertRegex(html, r'<button[^>]*aria-controls="t-panel"[^>]*id="t-tab-b"')
        self.assertEqual(html.count("aria-controls"), 1, html)
        self.assertRegex(html, r'<div[^>]*aria-labelledby="t-tab-b"[^>]*id="t-panel"')

    def test_progress_clamps_aria_valuenow(self):
        over = str(Progress(value=150, max=100))
        self.assertIn('aria-valuenow="100"', over)
        under = str(Progress(value=-5, max=100))
        self.assertIn('aria-valuenow="0"', under)
        inside = str(Progress(value=40, max=100))
        self.assertIn('aria-valuenow="40"', inside)
        self.assertIn('aria-valuenow="40.5"', str(Progress(value=40.5)))
        self.assertIn('aria-valuenow="0"', str(Progress(value=float("nan"))))

    def test_progress_string_value(self):
        self.assertIn('aria-valuenow="50"', str(Progress(value="50")))
        self.assertIn('aria-valuenow="100"', str(Progress(value="150")))

    def test_progress_non_positive_max(self):
        for top in (0, -10):
            with self.subTest(max=top):
                html = str(Progress(value=5, max=top))
                self.assertIn('aria-valuemax="0"', html)
                self.assertIn('aria-valuenow="0"', html)


if __name__ == "__main__":
    unittest.main()
