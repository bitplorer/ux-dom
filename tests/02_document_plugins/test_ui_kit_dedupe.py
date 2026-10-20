"""Locking tests for UI kit drift fixed by the dedupe refactor (D6, D7, D9; audit #59)."""

from __future__ import annotations

import re
import unittest

from ux_dom.ui import (
    Alert,
    Carousel,
    Dialog,
    Pagination,
    Sheet,
    ToastItem,
    field_classes,
    textarea_classes,
)


def _classes(html: str, tag: str) -> list[str]:
    return re.findall(rf'<{tag}\b[^>]*\bclass="([^"]*)"', html)


class TestOverlayPanelDrift(unittest.TestCase):
    def test_sheet_panel_is_labelled_and_focusable_like_dialog(self):
        html = str(Sheet(open=True, title="Filters", body="b"))
        self.assertIn('aria-labelledby="dialog-title"', html)
        self.assertIn('id="dialog-title"', html)
        self.assertIn('tabindex="-1"', html)

    def test_dialog_and_sheet_share_panel_body_spacing(self):
        kw = dict(open=True, title="T", body="B", footer="F")
        dialog_divs = _classes(str(Dialog(**kw)), "div")
        sheet_divs = _classes(str(Sheet(**kw)), "div")
        # body + footer are the last two divs inside the panel
        self.assertEqual(dialog_divs[-2:], sheet_divs[-2:])


class TestNavButtonDrift(unittest.TestCase):
    def test_carousel_and_pagination_nav_buttons_share_chrome(self):
        car = _classes(str(Carousel(slides=["a", "b", "c"], index=1)), "button")
        pag = _classes(str(Pagination(page=2, total_pages=3)), "button")
        self.assertEqual(set(car), set(pag))
        self.assertEqual(len(set(car)), 1)


class TestStatusTableDrift(unittest.TestCase):
    def test_toast_and_alert_use_one_status_table(self):
        pairs = {"success": "success", "warning": "warning", "error": "destructive"}
        for level, variant in pairs.items():
            with self.subTest(level=level):
                toast = _classes(str(ToastItem("x", level=level)), "li")[0]
                alert = _classes(str(Alert("x", variant=variant)), "div")[0]
                tone = toast.removeprefix("rounded-lg border px-3 py-2 shadow-sm ")
                self.assertIn(tone, alert)


class TestFieldClassesHeight(unittest.TestCase):
    def test_textarea_classes_is_field_classes_with_its_height(self):
        for invalid in (False, True):
            self.assertEqual(
                textarea_classes(className="x", invalid=invalid),
                field_classes(className="x", invalid=invalid, height="min-h-[5rem]"),
            )

    def test_field_classes_default_unchanged(self):
        self.assertTrue(field_classes().startswith("flex min-h-11 h-11 w-full "))


if __name__ == "__main__":
    unittest.main()
