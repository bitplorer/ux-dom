"""htmx search: the same endpoint returns a fragment for htmx and a full
page otherwise.

    uvicorn examples.standalone.search:app --reload     # from the repo root

``request.state.htmx`` is set by the middleware ``Htmx(middleware=True)``
installs. The result list is streamed with ``StreamingRoute``.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Request

from ux_dom import Component, Document
from ux_dom.dom import button, div, form, input_, label, span, title
from ux_dom.response.fastapi import StreamingRoute
from ux_dom.runtime import Csp, Htmx


class ResultList(Component):
    def render(self, q: str, n: int = 30):
        if not q:
            return div(span("type to search", id="msg"), id="results")
        hits = [div(f"{q}-{i}", id=f"r{i}", className="hit") for i in range(n)]
        return div(span(f"results for {q}", id="msg"), *hits, id="results")


class SearchBox(Component):
    def render(self, q: str = ""):
        return div(
            form(
                label("Search ", input_(name="q", value=q, id="q", type="search")),
                button("Go", type="submit"),
                action="/search",
                method="get",
                hx_get="/search",
                hx_target="#results",
                hx_swap="outerHTML",
                id="sf",
            ),
            ResultList(q=q),
            id="search-app",
        )


def create_app() -> FastAPI:
    document = Document().use(Htmx(version="2.0.4", middleware=True), Csp.auto())
    app = FastAPI(title="ux-dom htmx search")

    def page(q: str = ""):
        return document(SearchBox(q=q), head=[title("Search")])

    def search(request: Request, q: str = ""):
        if request.state.htmx:
            return ResultList(q=q)
        return page(q)

    routes = APIRouter(route_class=StreamingRoute)
    routes.add_api_route("/", page)
    routes.add_api_route("/search", search)
    routes.add_api_route("/health", lambda: {"ok": True})
    app.include_router(routes)
    document.mount(app)
    return app


app = create_app()
