"""ux_dom.ui kit — pure components + channel bridge soft-deps + copy."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from ux_dom.ui import (
    Alert,
    Badge,
    Button,
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    Input,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
    cn,
)
from ux_dom.ui.catalog import CATALOG, list_components
from ux_dom.ui.channel_bridge import (
    channel_available,
    live_button,
    stamp_region,
    to_fragment,
)
from ux_dom.ui.copy import UiCopyError, copy_component


class TestTokens(unittest.TestCase):
    def test_cn(self):
        self.assertEqual(cn("a", None, False, "b"), "a b")


class TestComponentsRender(unittest.TestCase):
    def test_button_variants(self):
        html = str(Button("Go", variant="destructive", size="sm"))
        self.assertIn("Go", html)
        self.assertIn("bg-red-600", html)
        self.assertIn("<button", html)

    def test_card_and_input(self):
        html = str(
            Card(
                CardHeader(CardTitle("T")),
                CardContent(Input(name="q", placeholder="search")),
            )
        )
        self.assertIn("T", html)
        self.assertIn('name="q"', html)
        self.assertIn("rounded-xl", html)

    def test_badge_alert_table(self):
        self.assertIn("ok", str(Badge("ok", variant="success")))
        self.assertIn('role="alert"', str(Alert("x")))
        html = str(
            Table(
                TableHeader(TableRow(TableHead("A"))),
                TableBody(TableRow(TableCell("1"))),
            )
        )
        self.assertIn("<table", html)
        self.assertIn("1", html)

    def test_htmx_passthrough(self):
        html = str(Button("X", hx_get="/z", hx_target="#t"))
        self.assertTrue("hx-get" in html or "hx_get" in html or "/z" in html)


class TestChannelBridgeSoft(unittest.TestCase):
    def test_no_channel_required(self):
        # Must not raise
        _ = channel_available()
        html = str(live_button("Ping", action="Demo.ping"))
        self.assertIn("Ping", html)
        self.assertIn("data-channel-action", html)
        frag = to_fragment(Button("A"))
        self.assertIn("A", frag)
        stamped = str(stamp_region(Card(CardContent("c")), uid="R:1"))
        self.assertIn("data-channel-id", stamped)
        self.assertIn("R:1", stamped)


class TestCopy(unittest.TestCase):
    def test_copy_button(self):
        with TemporaryDirectory() as td:
            dest = Path(td) / "ui"
            p = copy_component("Button", dest_dir=dest)
            self.assertTrue(p.is_file())
            self.assertTrue((dest / "tokens.py").is_file())
            text = p.read_text()
            self.assertIn("from .tokens import", text)
            with self.assertRaises(UiCopyError):
                copy_component("Button", dest_dir=dest)
            copy_component("button", dest_dir=dest, force=True)

    def test_catalog(self):
        self.assertIn("button", CATALOG)
        self.assertTrue(list_components())


class TestGalleryApp(unittest.TestCase):
    def test_gallery_200(self):
        root = Path(__file__).resolve().parents[2] / "examples" / "ux_kit"
        if not root.is_dir():
            self.skipTest("no examples/ux_kit")
        sys.path.insert(0, str(root))
        # ensure ux_dom on path
        repo = Path(__file__).resolve().parents[2]
        if str(repo) not in sys.path:
            sys.path.insert(0, str(repo))
        for k in list(sys.modules):
            if k == "app" or k.startswith("app."):
                del sys.modules[k]
        try:
            from app.main import app

            c = TestClient(app)
            r = c.get("/index/Index")
            self.assertEqual(r.status_code, 200, r.text[:300])
            self.assertIn("UxDom UI kit", r.text)
            self.assertIn("Button", r.text or "Default")
            self.assertIn("bg-slate-900", r.text)
        finally:
            for k in list(sys.modules):
                if k == "app" or k.startswith("app."):
                    del sys.modules[k]
            if str(root) in sys.path:
                sys.path.remove(str(root))


if __name__ == "__main__":
    unittest.main()
