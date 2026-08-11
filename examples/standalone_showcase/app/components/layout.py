"""Shared page chrome for the standalone showcase."""
from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, div, footer, header, main, nav, span


class Shell(Component):
    def render(self, *children, active: str = "home"):
        def link(label: str, href: str, key: str):
            cls = "nav-link active" if active == key else "nav-link"
            return a(label, href=href, className=cls)

        return div(
            header(
                nav(
                    a("UxDom Showcase", href="/", className="brand"),
                    link("Home", "/index/Index", "home"),
                    link("Shop", "/shop/Shop", "shop"),
                    link("Cart", "/cart/Cart", "cart"),
                    link("Live SSE", "/sse/SseDemo", "sse"),
                    link("Stream", "/stream/StreamDemo", "stream"),
                    className="nav",
                ),
                className="site-header",
            ),
            main(*children, className="site-main", id="content"),
            footer(
                span("Standalone UxDom example · no uxchannel required"),
                className="site-footer",
            ),
            className="shell min-h-screen bg-slate-50 text-slate-900",
            id="app",
        )
