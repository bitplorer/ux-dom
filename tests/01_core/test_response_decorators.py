"""``html_response`` / ``streaming_response`` decorator call forms.

Every form the signature advertises works: ``@deco``, ``@deco()``, ``deco(fn)``,
for sync and async endpoints. Non-renderable results pass through untouched.
"""
from __future__ import annotations

import asyncio
import inspect
import unittest

from ux_dom.dom import div
from ux_dom.response.starlette import (
    HTMLResponse,
    StreamingResponse,
    html_response,
    streaming_response,
)

_CASES = (
    (html_response, HTMLResponse),
    (streaming_response, StreamingResponse),
)


def _call(fn):
    out = fn()
    return asyncio.run(out) if inspect.iscoroutine(out) else out


def _endpoints():
    def sync_ep():
        """sync doc"""
        return div("x")

    async def async_ep():
        """async doc"""
        return div("x")

    return sync_ep, async_ep


class TestDecoratorCallForms(unittest.TestCase):
    def test_bare_decorator(self):
        for deco, cls in _CASES:
            for ep in _endpoints():
                with self.subTest(deco=deco.__name__, ep=ep.__name__):
                    wrapped = deco(ep)
                    self.assertIsInstance(_call(wrapped), cls)
                    self.assertEqual(wrapped.__name__, ep.__name__)
                    self.assertEqual(wrapped.__doc__, ep.__doc__)
                    self.assertEqual(
                        inspect.iscoroutinefunction(wrapped),
                        inspect.iscoroutinefunction(ep),
                    )

    def test_decorator_with_parentheses(self):
        for deco, cls in _CASES:
            for ep in _endpoints():
                with self.subTest(deco=deco.__name__, ep=ep.__name__):
                    wrapped = deco()(ep)
                    self.assertIsInstance(_call(wrapped), cls)
                    self.assertEqual(wrapped.__name__, ep.__name__)
                    self.assertEqual(
                        inspect.iscoroutinefunction(wrapped),
                        inspect.iscoroutinefunction(ep),
                    )

    def test_non_renderable_passes_through(self):
        sentinel = object()

        def sync_ep():
            return sentinel

        async def async_ep():
            return sentinel

        for deco, _cls in _CASES:
            for ep in (sync_ep, async_ep):
                with self.subTest(deco=deco.__name__, ep=ep.__name__):
                    self.assertIs(_call(deco(ep)), sentinel)

    def test_html_body(self):
        self.assertIn(b"x", _call(html_response()(_endpoints()[0])).body)


if __name__ == "__main__":
    unittest.main()
