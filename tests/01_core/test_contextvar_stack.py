"""ContextVar build stack — sync and async isolation."""

from __future__ import annotations

import asyncio
import unittest

from ux_dom.dom import div, span
from ux_dom.dom.src.dom_tag import context_stack, get_current


class TestContextVarStack(unittest.TestCase):
    def test_sync_with_stack(self):
        self.assertEqual(context_stack(), [])
        with div(id="r") as root:
            self.assertIs(get_current(), root)
            self.assertEqual(len(context_stack()), 1)
            span("x")
        self.assertEqual(context_stack(), [])
        self.assertIn("x", str(root))

    def test_nested_sync(self):
        with div(id="o") as outer:
            with span(id="i") as inner:
                self.assertIs(get_current(), inner)
            self.assertIs(get_current(), outer)

    def test_async_with_uses_same_api(self):
        async def run():
            async with div(id="a") as root:
                self.assertIs(get_current(), root)
                span("y")
            return root

        root = asyncio.run(run())
        self.assertIn("y", str(root))

    def test_concurrent_async_tasks_isolated(self):
        async def builder(i: int):
            async with div(id=f"t{i}") as root:
                await asyncio.sleep(0)
                # stack must be this task only
                cur = get_current()
                assert cur is root, (cur, root)
                span(f"c{i}")
                await asyncio.sleep(0)
            return str(root)

        async def main():
            return await asyncio.gather(*[builder(i) for i in range(20)])

        results = asyncio.run(main())
        for i, html in enumerate(results):
            self.assertIn(f'id="t{i}"', html)
            self.assertRegex(html, rf"\bc{i}\b")
            for j in range(20):
                if j != i:
                    self.assertNotRegex(html, rf"\bc{j}\b")


if __name__ == "__main__":
    unittest.main()
