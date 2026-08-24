"""DirectoryRouter path mapping, [param] segments, and include behaviour."""
from __future__ import annotations

import sys
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ux_dom.routing.fastapi import (
    DirectoryRouter,
    StreamingRoute,
    _clean_url_prefix,
    _set_endpoint_name,
    _to_fastapi_path_params,
)


class TestPathCleaning(unittest.TestCase):
    def test_application_not_stripped_as_app(self):
        # Historical bug: "application".replace("app", "") == "lication"
        self.assertEqual(
            _clean_url_prefix("application/routes", "app"), "/application/routes"
        )

    def test_base_prefix_only(self):
        self.assertEqual(_clean_url_prefix("app", "app"), "")
        self.assertEqual(_clean_url_prefix("app/shop", "app"), "/shop")
        self.assertEqual(_clean_url_prefix("app/shop/_private", "app"), "/shop")
        self.assertEqual(_clean_url_prefix("app/app/nested", "app"), "/app/nested")

    def test_private_segments_removed(self):
        self.assertEqual(_clean_url_prefix("app/_hidden/visible", "app"), "/visible")

    def test_bracket_to_fastapi_param(self):
        self.assertEqual(_to_fastapi_path_params("/users/[id]"), "/users/{id}")
        self.assertEqual(_to_fastapi_path_params("/posts/{slug}"), "/posts/{slug}")

    def test_no_double_slash(self):
        p = _clean_url_prefix("app/shop", "app")
        self.assertFalse(p.startswith("//"))
        self.assertTrue(p == "" or p.startswith("/"))


class TestEndpointNaming(unittest.TestCase):
    def test_classmethod_name_does_not_crash(self):
        class C:
            @classmethod
            def get(cls):
                return "ok"

        bound = getattr(C, "get")
        wrapped = _set_endpoint_name(bound, "mod.C:get")
        # either setattr on __func__ or wrapper
        name = getattr(wrapped, "name", None) or getattr(
            getattr(wrapped, "__func__", None), "name", None
        )
        self.assertEqual(name, "mod.C:get")
        self.assertEqual(wrapped(), "ok")

    def test_function_name(self):
        def post():
            return 1

        fn = _set_endpoint_name(post, "mod:post")
        self.assertEqual(fn.name, "mod:post")


class TestDirectoryRouterIntegration(unittest.TestCase):
    def test_component_routes_register_with_package_dir(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            pkg = root / "pkg"
            (pkg / "app").mkdir(parents=True)
            (pkg / "__init__.py").write_text("")
            (pkg / "app" / "__init__.py").write_text("")
            (pkg / "app" / "counter.py").write_text(textwrap.dedent("""
                from ux_dom.dom import Component, div
                __all__ = ["Counter"]
                class Counter(Component):
                    routes = ["get", "increment"]
                    def render(self, count=0):
                        return div(count)
                    @classmethod
                    def get(cls, count: int = 0):
                        return cls(count=count)
                    @classmethod
                    def increment(cls, count: int = 0):
                        return cls(count=count + 1)
                """))
            (pkg / "app" / "shop").mkdir()
            (pkg / "app" / "shop" / "__init__.py").write_text("")
            (pkg / "app" / "shop" / "route.py").write_text(textwrap.dedent("""
                __all__ = ["get", "cart"]
                def get(): return "g"
                def cart(): return "c"
                """))
            (pkg / "app" / "users" / "[id]").mkdir(parents=True)
            (pkg / "app" / "users" / "__init__.py").write_text("")
            (pkg / "app" / "users" / "[id]" / "__init__.py").write_text("")
            (pkg / "app" / "users" / "[id]" / "route.py").write_text(
                "def get(id: str): return id\n"
            )

            sys.path.insert(0, str(root))
            try:
                router = DirectoryRouter(
                    base_directory="app",
                    package_dir=pkg,
                    prefix="/v1",
                    route_class=StreamingRoute,
                )
            finally:
                sys.path.remove(str(root))

            # FastAPI 0.141+ wraps include_router as _IncludedRouter — use OpenAPI
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            paths = sorted(app.openapi().get("paths", {}))
            joined = " ".join(paths)
            self.assertTrue(any("counter" in p for p in paths), paths)
            self.assertTrue(any("{id}" in p for p in paths), paths)
            self.assertFalse(any("[id]" in p for p in paths), paths)
            self.assertTrue(any("shop" in p for p in paths), paths)
            self.assertTrue(any(p.startswith("/v1/") for p in paths), paths)


class TestStreamingRouteCompat(unittest.TestCase):
    def test_strict_content_type_accepted(self):
        def ep():
            return "x"

        # Must not TypeError on modern FastAPI
        route = StreamingRoute(path="/t", endpoint=ep, strict_content_type=False)
        self.assertEqual(route.path, "/t")


if __name__ == "__main__":
    unittest.main()
