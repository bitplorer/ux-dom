"""Production smoke for examples/ (ux_dom-only + ux-channel)."""

from __future__ import annotations

import sys
import unittest

from fastapi.testclient import TestClient


class TestHypermediaShop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from examples.ux_dom_only.hypermedia_shop.app import app

        cls.client = TestClient(app)

    def test_health_and_catalog(self):
        self.assertTrue(self.client.get("/health").json()["ok"])
        r = self.client.get("/shop/index/Index")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Hypermedia", r.text)
        r = self.client.get("/shop/products/list/ProductList")
        self.assertIn("Aurora", r.text)
        r = self.client.get("/shop/products/sku-a/")
        self.assertIn("Aurora Ring", r.text)

    def test_cart_get_post(self):
        r = self.client.get("/shop/cart/counter/CartCounter")
        self.assertIn("cart-root", r.text)
        r = self.client.post("/shop/cart/counter/CartCounter")
        self.assertEqual(r.status_code, 200)
        self.assertIn("cart-root", r.text)
        # DOM get not broken on class
        from examples.ux_dom_only.hypermedia_shop.shop_routes.cart.counter import (
            CartCounter,
        )

        inst = CartCounter()
        self.assertTrue(inst.get(id="count"))


class TestRealtimeKit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from examples.ux_dom_only.realtime_kit.app import app

        cls.client = TestClient(app)

    def test_pages_sse_ws_stream(self):
        self.assertTrue(self.client.get("/health").json()["ok"])
        self.assertIn("Realtime", self.client.get("/").text)
        body = self.client.get("/api/sse/market?n=3").text
        self.assertIn("event: message", body)
        self.assertIn("market:0", body)
        with self.client.websocket_connect("/ws/counter") as ws:
            self.assertEqual(ws.receive_json()["event"], "hello")
            ws.send_json({"event": "bump", "data": {"delta": 3}})
            self.assertEqual(ws.receive_json()["data"]["n"], 3)
        self.assertIn("Streamed", self.client.get("/stream").text)


@unittest.skipUnless(
    "ux_channel" in sys.modules
    or __import__("importlib").util.find_spec("ux_channel") is not None,
    "uxchannel not installed",
)
class TestLiveCart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from examples.with_ux_channel.live_cart.app import app

        cls.client = TestClient(app)

    def test_page_and_health(self):
        self.assertTrue(self.client.get("/health").json()["ok"])
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Live Cart", r.text)
        self.assertTrue(
            "data-channel-action" in r.text
            or "data_channel_action" in r.text
            or "uid" in r.text
        )


@unittest.skipUnless(
    "ux_channel" in sys.modules
    or __import__("importlib").util.find_spec("ux_channel") is not None,
    "uxchannel not installed",
)
class TestMarketBoard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from examples.with_ux_channel.market_board.app import app

        cls.client = TestClient(app)

    def test_page(self):
        self.assertTrue(self.client.get("/health").json()["ok"])
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Ticker", r.text)


if __name__ == "__main__":
    unittest.main()
