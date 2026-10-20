"""Htmx string-form route decorator (F3) and partial detection (F4)."""

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ux_dom.htmx import Htmx
from ux_dom.plugins.control.htmx import HtmxControl

VERBS = ("get", "post", "put", "patch", "delete")


class TestHtmxStringRoute(unittest.TestCase):
    def test_string_form_routes_the_decorated_function(self):
        for verb in VERBS:
            with self.subTest(verb=verb):
                app = FastAPI()
                h = Htmx(api=app, prefix="/a")

                @getattr(h, verb)("named")
                def handler():
                    return {"ok": verb}

                self.assertEqual(handler.__name__, "handler")
                r = TestClient(app).request(verb.upper(), "/a/named")
                self.assertEqual(r.status_code, 200, r.text)
                self.assertEqual(r.json(), {"ok": verb})
                self.assertIn("named", h.get_events(f"hx-{verb}"))


class TestHtmxPartialPolicy(unittest.TestCase):
    def _policy(self, headers):
        class Req:
            pass

        req = Req()
        req.headers = headers  # type: ignore[attr-defined]
        return HtmxControl().partial_policy(req)

    def test_hx_request_false_is_full(self):
        self.assertEqual(self._policy({"HX-Request": "false"}), "full")

    def test_history_restore_is_full(self):
        headers = {"hx-request": "true", "hx-history-restore-request": "true"}
        self.assertEqual(self._policy(headers), "full")

    def test_hx_request_true_is_partial(self):
        self.assertEqual(self._policy({"HX-Request": "true"}), "partial")

    def test_no_headers_is_full(self):
        self.assertEqual(self._policy(None), "full")


if __name__ == "__main__":
    unittest.main()
