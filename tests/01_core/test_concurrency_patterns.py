"""Concurrent safety: per-tree locks + isolation for independent trees."""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
import unittest

from ux_dom.dom import div, span
from ux_dom.dom.uniqueid import uniqueid
from ux_dom.web_io import WebSocketAdapter, WebSocketEvents


class TestSafePatterns(unittest.TestCase):
    def test_concurrent_render_frozen_tree(self):
        root = div(*[span(str(i), id=f"i{i}") for i in range(40)], id="r")
        with concurrent.futures.ThreadPoolExecutor(12) as ex:
            outs = list(ex.map(lambda _: root.__render__(pretty=False), range(80)))
        self.assertEqual(len(set(outs)), 1)

    def test_thread_owned_build(self):
        def work(i):
            with div(id=f"r{i}") as r:
                for j in range(10):
                    span(str(j))
            return r.__render__(pretty=False)

        with concurrent.futures.ThreadPoolExecutor(12) as ex:
            outs = list(ex.map(work, range(30)))
        for i, h in enumerate(outs):
            self.assertIn(f"r{i}", h)

    def test_async_with_isolation(self):
        async def one(i):
            async with div(id=f"a{i}") as r:
                span(str(i))
                await asyncio.sleep(0)
            return r.__render__(pretty=False)

        async def run():
            return await asyncio.gather(*[one(i) for i in range(25)])

        outs = asyncio.run(run())
        for i, h in enumerate(outs):
            self.assertIn(f"a{i}", h)

    def test_uniqueid_concurrent(self):
        bag = []
        lock = threading.Lock()

        def gen(_):
            local = [uniqueid() for _ in range(100)]
            with lock:
                bag.extend(local)

        with concurrent.futures.ThreadPoolExecutor(10) as ex:
            list(ex.map(gen, range(10)))
        self.assertEqual(len(bag), len(set(bag)))

    def test_ws_per_connection_isolation(self):
        class Box:
            def __init__(self):
                self.n = 0
                self.hist = []

        ad = WebSocketAdapter(Box, WebSocketEvents())

        class Fake:
            pass

        async def run():
            socks = [Fake() for _ in range(20)]
            await asyncio.gather(*[ad.ensure_instance(s) for s in socks])

            async def bump(i):
                inst = ad._instance_for(socks[i])
                for _ in range(10):
                    inst.n += 1
                    inst.hist.append(i)

            await asyncio.gather(*[bump(i) for i in range(20)])
            for i in range(20):
                inst = ad._instance_for(socks[i])
                self.assertEqual(inst.n, 10)
                self.assertTrue(all(x == i for x in inst.hist))
            for s in socks:
                ad.release_instance(s)
            self.assertEqual(len(ad._instances), 0)

        asyncio.run(run())

    def test_local_build_plus_shared_read(self):
        shared = div("frozen", id="shared")

        def work(i):
            with div(id=f"w{i}") as r:
                span(str(i))
            shared.__render__(pretty=False)
            return r.__render__(pretty=False)

        with concurrent.futures.ThreadPoolExecutor(10) as ex:
            outs = list(ex.map(work, range(20)))
        for i, h in enumerate(outs):
            self.assertIn(f"w{i}", h)


if __name__ == "__main__":
    unittest.main()
