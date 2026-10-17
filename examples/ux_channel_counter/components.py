"""ux-dom components. They know nothing about signing or transport."""

from __future__ import annotations

from markupsafe import Markup

from ux_dom import Component
from ux_dom.dom import div, output, p, span


class CounterCard(Component):
    def render(self, count: int):
        return div(
            p("Current count", className="label"),
            output(str(count), className="value"),
            id="count",
            data_count=str(count),
            className="card",
        )


class Region(Component):
    """Server-render a channel region inside a ux-dom tree.

    ``ch.html(region)`` returns HTML that ux-channel produced (the region
    wrapped in ``data-channel-id``). It is trusted, so it is marked with
    ``Markup`` and returned from ``render``, where ux-dom honours ``__html__``.
    """

    def render(self, html: str):
        return Markup(html)


class Hint(Component):
    def render(self):
        return p(
            span("Buttons carry "),
            span("data-channel-action", className="mono"),
            span(" and a signed "),
            span("data-channel-cap", className="mono"),
            span(". Changing their arguments in the browser breaks the signature."),
            className="hint",
        )
