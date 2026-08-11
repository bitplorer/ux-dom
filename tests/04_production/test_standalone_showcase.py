"""Smoke the examples/standalone_showcase app."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2] / "examples" / "standalone_showcase"


class TestStandaloneShowcase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT))
        for k in list(sys.modules):
            if k == "app" or k.startswith("app."):
                del sys.modules[k]
        from app.main import app

        cls.client = TestClient(app)

    def test_health_and_pages(self):
        self.assertTrue(self.client.get("/health").json()["ok"])
        self.assertIn("Showcase", self.client.get("/index/Index").text)
        self.assertIn("Aurora", self.client.get("/shop/Shop").text)
        self.assertIn("cart-root", self.client.get("/cart/Cart").text)
        self.assertEqual(self.client.post("/cart/Cart").status_code, 200)
        self.assertIn("SSE", self.client.get("/sse/SseDemo").text)
        self.assertIn("event: message", self.client.get("/api/sse?n=2").text)
        self.assertIn("Streamed", self.client.get("/api/stream").text)
