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
                    link("Home", "/", "home"),
                    link("Shop", "/shop", "shop"),
                    link("Cart", "/cart", "cart"),
                    link("Live SSE", "/sse", "sse"),
                    link("Stream", "/stream", "stream"),
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
