from __future__ import annotations

from ux_dom import Component
from ux_dom.dom import a, div, h1, li, p, ul

from ..document import page

__all__ = ["Index"]


class Index(Component):
    def render(self):
        return div(
            h1("UxDom XElement Kit", className="text-3xl font-bold mb-2"),
            p(
                "HTMX · Alpine · Web Components — Python definitions match ",
                "x_element.js (x-tagname → x-{name})",
                className="text-slate-600 mb-6",
            ),
            ul(
                li(
                    a(
                        "Light DOM (CustomElement) — full guide",
                        href="/lightdom",
                        className="text-sky-600 underline",
                    )
                ),
                li(
                    a(
                        "Shadow DOM (WebComponent) — full guide",
                        href="/shadowdom",
                        className="text-sky-600 underline",
                    )
                ),
                li(
                    a(
                        "Web Components quick demo",
                        href="/wc",
                        className="text-sky-600 underline",
                    )
                ),
                li(
                    a(
                        "Alpine + XElement",
                        href="/alpine",
                        className="text-sky-600 underline",
                    )
                ),
                li(
                    a(
                        "HTMX partials + XElement",
                        href="/htmx",
                        className="text-sky-600 underline",
                    )
                ),
                li(a("Jinja DSL", href="/jinja", className="text-sky-600 underline")),
                li(
                    a(
                        "Slots (named + helper)",
                        href="/slots",
                        className="text-sky-600 underline",
                    )
                ),
                className="list-disc pl-6 space-y-2",
            ),
            className="max-w-2xl mx-auto px-4 py-10",
            id="home",
        )


def get():
    return page(Index(), page_title="XElement Kit")
