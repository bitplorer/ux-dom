"""
Production-shaped hypermedia shop — **ux-dom only** (no ux-channel).

Capabilities shown
------------------
* Component + ``@classmethod`` routes (get/add) without shadowing DOM ``get``
* Plugin composition: FastAPIHost + DirectoryRouting + HtmxControl
* Streaming HTML partials + HtmxMiddleware
* File-based routes under ``shop_routes/`` (Next-style ``[id]``)

DirectoryRouting URL shape (0.1)::

    shop_routes/index.py::Index.get
        → GET /{prefix}/index/Index   e.g. /shop/index/Index
    shop_routes/products/list.py::ProductList.get
        → GET /shop/products/list/ProductList

Run::

    uvicorn examples.ux_dom_only.hypermedia_shop.app:app --host 0.0.0.0 --port 8092
"""
from __future__ import annotations

from pathlib import Path

from fastapi.responses import JSONResponse, RedirectResponse

from ux_dom.plugins import App
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.host import FastAPIHost
from ux_dom.plugins.routing import DirectoryRouting

PACKAGE = Path(__file__).resolve().parent

# Canonical home route produced by DirectoryRouting for shop_routes/index.py
HOME = "/shop/index/Index"

app = (
    App(debug=False)
    .use(FastAPIHost(title="ux-dom Shop", debug=False))
    .use(
        DirectoryRouting(
            package_dir=PACKAGE,
            base_directory="shop_routes",
            prefix="/shop",
        )
    )
    .use(HtmxControl(middleware=True, version="2.0.4"))
    .build()
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
    """Friendly entry — DirectoryRouting does not auto-map prefix root."""
    return RedirectResponse(HOME)
