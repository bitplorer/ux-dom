"""F-18 absence lock: ux-dom ships no file router and no route/DOM hook.

Product page routes are ``ux_compose.routing.DirectoryRoutes``.
"""
from __future__ import annotations

import importlib
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "ux_dom"


class TestRouterModulesAbsent(unittest.TestCase):
    def test_routing_modules_do_not_import(self):
        for mod in (
            "ux_dom.routing",
            "ux_dom.routing.fastapi",
            "ux_dom.plugins.routing",
        ):
            with self.subTest(mod=mod), self.assertRaises(ImportError):
                importlib.import_module(mod)

    def test_routing_dirs_absent_on_disk(self):
        self.assertFalse((SRC / "routing").exists())
        self.assertFalse((SRC / "plugins" / "routing").exists())

    def test_no_routing_plugin_protocol(self):
        from ux_dom.plugins import protocols

        self.assertFalse(hasattr(protocols, "RoutingPlugin"))

    def test_app_has_no_routing_surface(self):
        from ux_dom.plugins import App

        for name in ("routes", "use_routing", "add_routing"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(App, name))

    def test_no_router_diagnostics(self):
        from ux_dom import diagnostics

        for name in ("directory_router_missing_base", "directory_router_no_package_dir"):
            self.assertFalse(hasattr(diagnostics, name), name)


class TestComponentHookAbsent(unittest.TestCase):
    def test_no_custom_getattribute(self):
        from ux_dom import Component
        from ux_dom.dom.src import component as component_mod

        self.assertNotIn("__getattribute__", vars(Component))
        self.assertFalse(hasattr(component_mod, "_DOM_INSTANCE_API"))

    def test_dom_api_on_plain_component(self):
        from ux_dom import Component
        from ux_dom.dom import div, span

        class Plain(Component):
            def render(self):
                return div(span("x", id="x"), id="p")

        p = Plain()
        self.assertTrue(p.get(id="x"))
        p._clear()
        self.assertEqual(len(p), 0)


class TestCliAddRouteAbsent(unittest.TestCase):
    def test_add_route_helpers_gone(self):
        from ux_dom.cli import adders

        for name in ("add_route", "_ensure_route_packages", "_parse_methods"):
            self.assertFalse(hasattr(adders, name), name)

    def test_uxdom_add_route_exits_2(self):
        proc = subprocess.run(
            [sys.executable, "-m", "ux_dom.cli.cli", "add", "route", "about"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)


class TestRouterDemosAbsent(unittest.TestCase):
    def test_router_demo_dirs_gone(self):
        for rel in (
            "examples/ux_dom_only/hypermedia_shop",
            "examples/standalone_showcase",
        ):
            self.assertFalse((ROOT / rel).exists(), rel)

    def test_no_router_import_in_src_examples_standalone(self):
        needles = ("ux_dom.routing", "ux_dom.plugins.routing", "DirectoryRouting(")
        hits = []
        for base in ("src", "examples", "standalone"):
            for py in (ROOT / base).rglob("*.py"):
                text = py.read_text(encoding="utf-8", errors="replace")
                hits += [f"{py.relative_to(ROOT)}: {n}" for n in needles if n in text]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
