"""Context stack isolation under asyncio (P0 correctness)."""

from __future__ import annotations

import asyncio
import unittest

from ux_dom.dom import div


class TestAsyncContextIsolation(unittest.TestCase):
    def test_concurrent_tasks_do_not_corrupt_stack(self):
        async def build(label: str):
            # create_task isolation: each task gets own ContextVar stack
            await asyncio.sleep(0)
            with div(id=label) as root:
                await asyncio.sleep(0)
                with div(className="child"):
                    div(label)
            return root.__render__(pretty=False)

        async def main():
            t1 = asyncio.create_task(build("A"))
            t2 = asyncio.create_task(build("B"))
            a, b = await asyncio.gather(t1, t2)
            return a, b

        a, b = asyncio.run(main())
        self.assertIn('id="A"', a)
        self.assertIn('id="B"', b)
        # Each tree should contain only its own label as text content root path
        self.assertIn(">A<", a.replace("\n", ""))
        self.assertIn(">B<", b.replace("\n", ""))
        self.assertNotIn('id="B"', a)
        self.assertNotIn('id="A"', b)

    def test_async_with(self):
        async def build():
            async with div(id="aw") as root:
                async with div(className="inner"):
                    div("ok")
            return root.__render__(pretty=False)

        html = asyncio.run(build())
        self.assertIn('id="aw"', html)
        self.assertIn("ok", html)
        self.assertIn("inner", html)

    def test_nested_sync_still_works(self):
        with div("context") as context:
            with div("sub"):
                div("leaf")
        html = context.__render__()
        self.assertIn("context", html)
        self.assertIn("sub", html)
        self.assertIn("leaf", html)


if __name__ == "__main__":
    unittest.main()
