"""Locking tests for UI kit drift fixed by the dedupe refactor (D6, D7, D9; audit #59)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

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
from ux_dom.ui.copy import UiCopyError, copy_component

# tokens.py as an app copied it before the shared helpers existed
_OLD_TOKENS = '''
def cn(*parts):
    return " ".join(p for p in parts if isinstance(p, str) and p)

focus_ring = surface = type_scale = overlay = target = {}

def field_classes(*, className="", invalid=False):
    return cn("flex", className)
'''


def _classes(html: str, tag: str) -> list[str]:
    return re.findall(rf'<{tag}\b[^>]*\bclass="([^"]*)"', html)


class TestOverlayPanelDrift(unittest.TestCase):
    def test_sheet_panel_is_labelled_and_focusable_like_dialog(self):
        html = str(Sheet(open=True, title="Filters", body="b"))
        self.assertIn('aria-labelledby="overlay-title"', html)
        self.assertIn('id="overlay-title"', html)
        self.assertIn('tabindex="-1"', html)

    def test_title_id_follows_root_id_so_open_overlays_do_not_collide(self):
        page = str(Dialog(open=True, title="A", id="confirm")) + str(
            Sheet(open=True, title="B", id="filters")
        )
        ids = re.findall(r'\sid="([^"]+)"', page)
        self.assertEqual(len(ids), len(set(ids)), ids)
        self.assertIn('aria-labelledby="confirm-title"', page)
        self.assertIn('aria-labelledby="filters-title"', page)

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


class TestCopyOntoOlderTokens(unittest.TestCase):
    def _seed(self, td: str) -> Path:
        dest = Path(td) / "ui"
        dest.mkdir()
        (dest / "tokens.py").write_text(_OLD_TOKENS, encoding="utf-8")
        return dest

    def test_missing_name_in_kept_tokens_is_reported(self):
        for name in ("dialog", "sheet", "command", "carousel", "pagination", "tabs", "toast", "alert"):
            with self.subTest(name=name), TemporaryDirectory() as td:
                dest = self._seed(td)
                with self.assertRaises(UiCopyError) as ctx:
                    copy_component(name, dest_dir=dest)
                self.assertIn("tokens.py: ", str(ctx.exception))
                self.assertIn("--force", str(ctx.exception))
                self.assertFalse((dest / f"{name}.py").exists())

    def test_missing_keyword_in_kept_tokens_is_reported(self):
        with TemporaryDirectory() as td:
            dest = self._seed(td)
            with self.assertRaises(UiCopyError) as ctx:
                copy_component("textarea", dest_dir=dest)
            self.assertIn("tokens.py: field_classes(height=)", str(ctx.exception))

    def test_force_refreshes_the_old_tokens(self):
        with TemporaryDirectory() as td:
            dest = self._seed(td)
            copy_component("dialog", dest_dir=dest, force=True)
            self.assertIn("def dialog_panel", (dest / "tokens.py").read_text())

    def test_current_tokens_are_kept_without_error(self):
        with TemporaryDirectory() as td:
            dest = Path(td) / "ui"
            copy_component("button", dest_dir=dest)
            for name in ("dialog", "textarea", "toast"):
                copy_component(name, dest_dir=dest)


if __name__ == "__main__":
    unittest.main()
