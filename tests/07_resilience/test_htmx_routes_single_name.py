"""``HtmxRoutes`` is the route decorator; ``Htmx`` names only the document runtime."""
from __future__ import annotations

import unittest

import ux_dom
import ux_dom.htmx


class TestHtmxRoutesSingleName(unittest.TestCase):
    def test_router_decorator_is_htmx_routes(self):
        self.assertIn("HtmxRoutes", ux_dom.htmx.__all__)
        self.assertFalse(hasattr(ux_dom.htmx, "Htmx"))
        self.assertIsNot(ux_dom.Htmx, ux_dom.htmx.HtmxRoutes)


if __name__ == "__main__":
    unittest.main()
