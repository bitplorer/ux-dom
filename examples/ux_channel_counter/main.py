"""ASGI entry point.

    uvicorn examples.ux_channel_counter.main:app --reload    # from the repo root

Ownership: ux-dom builds the document and the markup; ux-channel boots the
action endpoint (``/ux-channel/action``), serves its client script, signs
controls and re-renders regions.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from ux_dom import Document
from ux_dom.dom import button, div, h1, link, main, meta, p, title
from ux_dom.response.fastapi import HTMLRoute
from ux_dom.runtime import Channel as ChannelScripts, Csp

from .channel import boot, register
from .components import Hint, Region

TITLE = "Counter · ux-dom × ux-channel"

app = FastAPI(title=TITLE)
ch = boot(app)
counter, add, reset = register(ch)

# ChannelScripts adds the same <script> tags as ux-channel's own helpers;
# Channel.boot already serves the files under /ux-channel/static.
document = Document(
    head=[
        meta(charset="utf-8"),
        meta(name="viewport", content="width=device-width, initial-scale=1"),
        link(rel="stylesheet", href="/static/app.css"),
    ],
).use(ChannelScripts(), Csp.auto())


def control_button(label: str, attrs, *, ghost: bool = False):
    """A plain button plus ux-channel ``ControlAttrs`` (via ``as_dict``)."""
    return button(
        label,
        type="button",
        className="ghost" if ghost else "primary",
        **attrs.as_dict(),
    )


def index():
    return document(
        main(
            h1("Counter"),
            p("ux-dom renders the page; ux-channel runs the actions."),
            Region(html=ch.html(counter)),
            div(
                control_button("+1", ch.control(add, trust_step=1)),
                control_button("+5", ch.control(add, trust_step=5)),
                control_button("Reset", ch.control(reset), ghost=True),
                className="row",
            ),
            Hint(),
            className="shell",
        ),
        head=[title(TITLE)],
    )


pages = APIRouter(route_class=HTMLRoute)
pages.add_api_route("/", index)
app.include_router(pages)
app.add_api_route("/health", lambda: {"ok": True, "app": "ux_channel_counter"})
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)
document.mount(app)
