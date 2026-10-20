"""Locking test for D1 (audit #59): FloatLegend renders like IntegerLegend."""

from __future__ import annotations

import unittest

from ux_dom.elements.floats import FloatLegend
from ux_dom.elements.integers import IntegerLegend


class TestFloatLegend(unittest.TestCase):
    def test_renders_legend(self):
        html = FloatLegend(label="L").__render__(pretty=False)
        self.assertEqual(html, IntegerLegend(label="L").__render__(pretty=False))
        self.assertIn("<legend", html)
        self.assertIn(">L<", html)


if __name__ == "__main__":
    unittest.main()
