"""Layout shared by every page."""

from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, div, footer, header, main, nav

NAV = (
    ("Home", "/"),
    ("Shop", "/shop"),
    ("Cart", "/cart"),
    ("Guestbook", "/guestbook"),
    ("Live", "/sse"),
    ("Stream", "/stream"),
)


class Shell(Component):
    def render(self, *children, active: str = "/"):
        links = [
            a(label, href=href, aria_current="page" if href == active else False)
            for label, href in NAV
        ]
        return div(
            header(nav(a("UxDom Showcase", href="/", className="brand"), *links)),
            main(*children, id="content"),
            footer("ux-dom only: no JavaScript build, no SPA."),
            className="shell",
        )
