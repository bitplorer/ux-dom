"""Guestbook: everything a visitor types is untrusted.

* ``name`` is a plain ``str``: ux-dom escapes it, so ``<b>`` shows as text.
* ``message`` is Markdown: ``MarkdownElement`` keeps the formatting and
  escapes raw HTML inside it.
* ``website`` goes into ``href``: a ``javascript:`` URL becomes inert.
* The announcement is HTML *we* wrote, so it is marked trusted with ``Markup``
  and returned from a component's ``render``: that is where ux-dom honours
  ``__html__``. (A ``Markup`` passed straight to a tag is escaped like any
  other string, which fails closed.)
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from fastapi import Form, Request
from fastapi.responses import RedirectResponse
from markupsafe import Markup

from ux_dom import Component
from ux_dom.dom import (
    a,
    button,
    form,
    h1,
    input_,
    label,
    li,
    p,
    span,
    strong,
    textarea,
    ul,
)
from ux_dom.dom.htmlelement import MarkdownElement

from ..components import Shell
from ..document import page


class Announcement(Component):
    def render(self):
        return Markup(
            '<p class="announcement">Be kind. <em>Markdown</em> is welcome.</p>'
        )


@dataclass(frozen=True)
class Entry:
    name: str
    website: str
    message: str


_lock = threading.Lock()
_entries: list[Entry] = []  # process-local demo state


class Entries(Component):
    def render(self, entries: list[Entry]):
        items = [
            li(
                strong(entry.name),
                " ",
                (
                    a("website", href=entry.website, rel="nofollow ugc")
                    if entry.website
                    else ""
                ),
                MarkdownElement(entry.message),
                className="card",
            )
            for entry in reversed(entries)
        ]
        return ul(*items, id="entries", className="entries")


class SignForm(Component):
    def render(self):
        return form(
            label("Name", input_(name="name", required=True, maxlength="60")),
            label("Website", input_(name="website", type="url", maxlength="200")),
            label("Message", textarea(name="message", required=True, rows="3")),
            button("Sign", type="submit"),
            method="post",
            action="/guestbook",
            hx_post="/guestbook",
            hx_target="#entries",
            hx_swap="outerHTML",
            className="card form",
        )


def get():
    with _lock:
        entries = list(_entries)
    return page(
        Shell(
            h1("Guestbook"),
            Announcement(),
            SignForm(),
            p(span(f"{len(entries)} entries")),
            Entries(entries=entries),
            active="/guestbook",
        ),
        page_title="Guestbook · UxDom Showcase",
    )


def post(
    request: Request,
    name: str = Form(..., max_length=60),
    message: str = Form(..., max_length=2000),
    website: str = Form("", max_length=200),
):
    with _lock:
        _entries.append(Entry(name=name, website=website, message=message))
        entries = list(_entries)
    if request.state.htmx:
        return Entries(entries=entries)
    return RedirectResponse("/guestbook", status_code=303)
