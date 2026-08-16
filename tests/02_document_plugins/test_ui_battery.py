"""Phase-1 battery: Slider, Carousel, Toast, DatePicker, Chart + completeness."""

from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from ux_dom.dom import div
from ux_dom.ui import (
    Carousel,
    Chart,
    DatePicker,
    Dialog,
    Slider,
    Table,
    TableBody,
    TableEmpty,
    TableHead,
    Tabs,
    ToastHost,
)
from ux_dom.ui.catalog import CATALOG, RUNTIMES
from ux_dom.ui.channel_bridge import (
    channel_available,
    live_button,
    public_form,
    stamp_region,
)
from ux_dom.ui.copy import copy_component


class TestBatteryRenders(unittest.TestCase):
    def test_slider_disabled_and_value(self):
        html = str(Slider(name="vol", value=40, min=0, max=100, show_value=True))
        self.assertIn('type="range"', html)
        self.assertIn("vol", html)
        self.assertIn("40", html)
        off = str(Slider(disabled=True, value=0))
        self.assertIn("disabled", off)

    def test_slider_no_false_disabled(self):
        html = str(Slider(value=10))
        self.assertNotRegex(html, r'(?<![:\w])disabled(?:=|\s|>)')

    def test_carousel_empty_and_slides(self):
        empty = str(Carousel(slides=[]))
        self.assertIn("No slides", empty)
        self.assertIn('data-carousel="empty"', empty)
        html = str(Carousel(slides=[div("One"), div("Two")], label="Highlights"))
        self.assertIn("One", html)
        self.assertIn("Two", html)
        self.assertIn("x-data", html)
        self.assertIn("Previous slide", html)
        self.assertIn("aria-roledescription", html)

    def test_toast_host_empty_and_items(self):
        empty = str(ToastHost(items=[]))
        self.assertIn("No notices", empty)
        self.assertIn('id="notices"', empty)
        self.assertIn("aria-live", empty)
        html = str(ToastHost(items=[{"text": "Saved", "level": "success"}]))
        self.assertIn("Saved", html)
        self.assertIn("data-level", html)

    def test_datepicker_states(self):
        html = str(DatePicker(name="due", value="2026-08-16"))
        self.assertIn('type="date"', html)
        self.assertIn("2026-08-16", html)
        bad = str(DatePicker(name="due", invalid=True))
        self.assertIn("aria-invalid", bad)
        off = str(DatePicker(name="due", disabled=True))
        self.assertIn("disabled", off)
        vacant = str(DatePicker(name="due"))
        self.assertIn("data-empty", vacant)

    def test_chart_empty_spark_bar(self):
        empty = str(Chart(series=[]))
        self.assertIn("No data", empty)
        self.assertIn('data-chart="empty"', empty)
        spark = str(Chart(series=[3, 5, 4, 8], kind="sparkline", label="Revenue"))
        self.assertIn("<svg", spark)
        self.assertIn("polyline", spark)
        self.assertIn("Revenue", spark)
        bars = str(Chart(series=[2, 7, 4], kind="bar"))
        self.assertIn("<rect", bars)

    def test_table_empty_and_sort(self):
        html = str(
            Table(
                TableBody(TableEmpty("Nothing here", col_span=3)),
            )
        )
        self.assertIn("Nothing here", html)
        head = str(TableHead("Name", sorted="asc"))
        self.assertIn("aria-sort", head)

    def test_dialog_a11y(self):
        html = str(Dialog(title="Confirm", body="Are you sure?"))
        self.assertIn('role="dialog"', html)
        self.assertIn("aria-modal", html)
        self.assertIn("Confirm", html)


class TestChannelOptional(unittest.TestCase):
    def test_every_battery_renders_without_channel(self):
        _ = channel_available()
        nodes = [
            Slider(value=1),
            Carousel(slides=["A"]),
            Carousel(slides=[]),
            ToastHost(items=[]),
            DatePicker(name="d"),
            Chart(series=[1, 2]),
            Tabs(items=[]),
            Dialog(body="x"),
        ]
        for node in nodes:
            html = str(node)
            self.assertTrue(html)

    def test_stamp_and_live_and_public_form(self):
        stamped = str(stamp_region(Dialog(body="inner"), uid="Checkout:dialog"))
        self.assertIn("data-channel-id", stamped)
        self.assertIn("Checkout:dialog", stamped)
        self.assertIn("inner", stamped)
        btn = str(live_button("Pay", action="Checkout.pay", target="Checkout:dialog"))
        self.assertIn("Pay", btn)
        self.assertIn("data-channel-action", btn)
        form = str(public_form("ok", action="orders.create"))
        self.assertIn("<form", form)
        self.assertIn("orders.create", form)
        self.assertIn("data-progressive", form)

    def test_morph_xelement_contract_markup(self):
        # Carousel is Alpine local chrome. After morph, stock x_element.js
        # re-upgrades hosts; app code does not implement re-upgrade.
        # This test locks the coexistence markup: stamped region keeps
        # x-data (Alpine) + data-channel-id (morph target).
        html = str(
            stamp_region(
                Carousel(slides=["Alpha", "Beta"], label="Hero"),
                uid="Hero:carousel",
            )
        )
        self.assertIn("data-channel-id", html)
        self.assertIn("Hero:carousel", html)
        self.assertIn("x-data", html)
        self.assertIn("Alpha", html)


class TestCatalogAndCopy(unittest.TestCase):
    def test_new_stems_in_catalog(self):
        for key in ("slider", "carousel", "toast", "datepicker", "chart"):
            self.assertIn(key, CATALOG)
            self.assertIn(key, RUNTIMES)

    def test_copy_datepicker_pulls_input(self):
        with TemporaryDirectory() as td:
            dest = Path(td) / "ui"
            copy_component("DatePicker", dest_dir=dest, force=True)
            self.assertTrue((dest / "datepicker.py").is_file())
            self.assertTrue((dest / "input.py").is_file())
            self.assertTrue((dest / "tokens.py").is_file())

    def test_copy_carousel(self):
        with TemporaryDirectory() as td:
            dest = Path(td) / "ui"
            p = copy_component("Carousel", dest_dir=dest)
            text = p.read_text(encoding="utf-8")
            self.assertIn("from .tokens import", text)
            self.assertNotIn("from ux_dom.ui.tokens", text)


if __name__ == "__main__":
    unittest.main()
