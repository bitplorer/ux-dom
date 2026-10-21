"""Production smoke for examples/ux_dom_only."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient


class TestRealtimeKit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from examples.ux_dom_only.realtime_kit.app import app

        cls.client = TestClient(app)

    def test_pages_sse_stream(self):
        self.assertTrue(self.client.get("/health").json()["ok"])
        self.assertIn("Realtime", self.client.get("/").text)
        body = self.client.get("/api/sse/market?n=3").text
        self.assertIn("event: message", body)
        self.assertIn("market:0", body)
        self.assertIn("Streamed", self.client.get("/stream").text)


if __name__ == "__main__":
    unittest.main()
