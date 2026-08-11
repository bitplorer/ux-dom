"""Landing — feature tour of pure UxDom."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, div, h1, h2, li, p, span, ul

from app.components.layout import Shell
from app.document import page

__all__ = ["Index"]


class Index(Component):
    routes = ["get"]

    def render(self):
        cards = [
            ("Components", "Declarative Python HTML with context managers"),
            ("DirectoryRouter", "Next-style file routes under app/routes/"),
            ("HTMX", "Partials and swaps without a JS SPA"),
            ("Streaming", "StreamingResponse for progressive HTML"),
            ("SSE", "Server-sent events for live ticks"),
            ("Tailwind", "Utility CSS via TailwindStyle plugin"),
        ]
        return Shell(
            h1("UxDom Standalone Showcase", className="text-3xl font-bold mb-2"),
            p(
                "A production-shaped app using only UxDom + FastAPI plugins — "
                "Components, DirectoryRouter, HTMX, SSE, and streaming HTML.",
                className="text-slate-600 mb-6 max-w-xl",
            ),
            div(
                *[
                    div(
                        h2(title, className="font-semibold text-lg mb-1"),
                        p(desc, className="text-sm text-slate-600"),
                        className="card",
                    )
                    for title, desc in cards
                ],
                className="grid gap-3 sm:grid-cols-2 mb-8",
            ),
            h2("Try it", className="text-xl font-semibold mb-3"),
            ul(
                li(a("Shop catalog →", href="/shop/Shop", className="text-sky-600 underline")),
                li(a("HTMX cart counter →", href="/cart/Cart", className="text-sky-600 underline")),
                li(a("SSE ticker →", href="/sse/SseDemo", className="text-sky-600 underline")),
                li(a("Streamed HTML →", href="/stream/StreamDemo", className="text-sky-600 underline")),
                className="list-disc pl-6 space-y-2 text-slate-700",
            ),
            p(
                span("Health: ", className="text-slate-500"),
                a(
                    "/health",
                    href="/health",
                    className="text-sky-600 underline font-mono text-sm",
                ),
                className="mt-8",
            ),
            active="home",
        )

    @classmethod
    def get(cls):
        return page(cls(), page_title="UxDom Showcase")
