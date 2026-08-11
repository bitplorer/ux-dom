"""HTMX partials + streaming HTML + DirectoryRouter-style components."""
from __future__ import annotations

from fastapi import FastAPI, Request

from ux_dom import Component, Document
from ux_dom.dom import div, span, button, form, input_
from ux_dom.htmx.middleware import HtmxMiddleware
from ux_dom.response.starlette import HTMLResponse, StreamingResponse


class SearchBox(Component):
    routes = ["get", "search"]  # shadow test under real app

    def render(self, q: str = ""):
        return div(
            form(
                input_(name="q", value=q, id="q"),
                button("Go", type="submit", hx_get="/search", hx_target="#results", hx_include="#q"),
                id="sf",
            ),
            div(
                span(f"results for {q}" if q else "type to search", id="msg"),
                id="results",
            ),
            id="search-app",
        )

    @classmethod
    def get(cls):
        return cls(q="")

    @classmethod
    def search(cls, q: str = ""):
        return cls(q=q)


class ResultList(Component):
    def render(self, q: str = "", n: int = 20):
        return div(
            *[div(f"{q}-{i}", id=f"r{i}", className="hit") for i in range(n)],
            id="list",
        )


def create_app() -> FastAPI:
    app = FastAPI(title="ux_dom-htmx-stream")
    app.add_middleware(HtmxMiddleware)
    doc = Document(ensure_csrf_token=False)

    @app.get("/")
    def home():
        return HTMLResponse(doc(SearchBox.get()))

    @app.get("/search")
    def search(request: Request, q: str = ""):
        # HTMX partial: only results fragment
        if getattr(request.state, "htmx", False):
            return StreamingResponse(ResultList(q=q, n=30))
        return HTMLResponse(doc(SearchBox(q=q)))

    @app.get("/stream-page")
    def stream_page():
        return StreamingResponse(SearchBox(q="streamed"))

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


app = create_app()
