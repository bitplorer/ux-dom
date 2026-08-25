"""
Production-shaped hypermedia shop — **ux-dom only** (no ux-channel).

Leftover example (cannot import ux-compose). Product apps:
``uxcompose create-app`` / ``ux_compose.build``.

Capabilities shown
------------------
* Component + ``@classmethod`` routes (get/add) without shadowing DOM ``get``
* Leftover plugin composition: DirectoryRouting + HtmxControl + FastAPI()
* Streaming HTML partials + HtmxMiddleware
* File-based routes under ``shop_routes/`` (leftover DirectoryRouter ``[id]``)

DirectoryRouting URL shape (leftover DirectoryRouter)::

    shop_routes/index.py::Index.get
        → GET /{prefix}/index/Index   e.g. /shop/index/Index
    shop_routes/products/list.py::ProductList.get
        → GET /shop/products/list/ProductList

Run::

    uvicorn examples.ux_dom_only.hypermedia_shop.app:app --host 0.0.0.0 --port 8092
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse

from ux_dom.plugins import App
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.routing import DirectoryRouting

PACKAGE = Path(__file__).resolve().parent

# Canonical home route produced by leftover DirectoryRouting for shop_routes/index.py
HOME = "/shop/index/Index"

app = (
    App(debug=False)
    .use(
        DirectoryRouting(
            package_dir=PACKAGE,
            base_directory="shop_routes",
            prefix="/shop",
        )
    )
    .use(HtmxControl(middleware=True, version="2.0.4"))
    .build(asgi=FastAPI(title="ux-dom Shop", debug=False))
)


@app.get("/health", response_class=JSONResponse)
def health():
    return {"ok": True, "app": "ux_dom_only.hypermedia_shop"}


@app.get("/")
def root():
    return RedirectResponse(HOME)


@app.get("/shop")
@app.get("/shop/")
def shop_alias():
    """Friendly entry — leftover DirectoryRouting does not auto-map prefix root."""
    return RedirectResponse(HOME)
