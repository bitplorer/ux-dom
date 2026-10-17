"""FastAPI route classes serialize ux-dom trees (moved from the removed router)."""
from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from ux_dom.dom import div
from ux_dom.response.fastapi import HTMLRoute, StreamingRoute


def _client(route_class) -> TestClient:
    router = APIRouter(route_class=route_class)

    @router.get("/items/{item_id}")
    def item(item_id: str):
        return div(f"item {item_id}", id="item")

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_html_route_renders_tree_with_path_params():
    r = _client(HTMLRoute).get("/items/7")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert '<div id="item">' in r.text and "item 7" in r.text


def test_streaming_route_streams_tree():
    r = _client(StreamingRoute).get("/items/a<b")
    assert r.status_code == 200
    assert "item a&lt;b" in r.text  # path param is text, escaped


def test_extra_route_kwargs_pass_through():
    route = StreamingRoute(path="/t", endpoint=lambda: "x", name="t", tags=["pages"])
    assert (route.path, route.name, route.tags) == ("/t", "t", ["pages"])
