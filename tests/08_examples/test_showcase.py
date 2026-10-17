"""examples/showcase: Document + Htmx + Csp, explicit routes, safe content."""

from __future__ import annotations

import re

import pytest
from example_checks import (
    assert_external_scripts_pinned,
    assert_htmx_csp_safe,
    assert_scripts_nonced,
    client,
    compact,
)


@pytest.fixture(scope="module")
def c():
    from examples.showcase.main import app

    return client(app)


def test_home_is_a_full_document_with_runtimes(c):
    r = c.get("/")
    assert r.status_code == 200
    assert r.text.lstrip().lower().startswith("<!doctype html>")
    assert re.search(r"<title>\s*UxDom Showcase\s*</title>", r.text)
    assert 'href="/static/app.css"' in r.text
    assert "https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js" in r.text
    assert_external_scripts_pinned(r.text)


def test_csp_header_and_nonced_scripts(c):
    r = c.get("/")
    assert "strict-dynamic" in r.headers["content-security-policy"]
    assert_htmx_csp_safe(r.text)
    assert_scripts_nonced(r)


def test_static_css_is_served(c):
    r = c.get("/static/app.css")
    assert r.status_code == 200
    assert "text/css" in r.headers["content-type"]


def test_shop_sanitizes_cms_html(c):
    r = c.get("/shop")
    assert r.status_code == 200
    html = compact(r.text)
    assert "Aurora Ring" in html
    assert "<strong>18k gold</strong>" in html  # formatting survives defHTML
    assert "onerror" not in html and "steal()" not in html
    assert "x-init" not in html


def test_cart_full_page_and_htmx_partial(c):
    page = c.get("/cart")
    assert page.status_code == 200
    assert 'hx-post="/cart"' in page.text  # relative, same-origin
    before = int(page.text.split('data-count="', 1)[1].split('"', 1)[0])
    partial = c.post("/cart", headers={"HX-Request": "true"})
    assert partial.status_code == 200
    assert "<html" not in partial.text
    assert f'data-count="{before + 1}"' in partial.text


def test_guestbook_escapes_user_content(c):
    r = c.post(
        "/guestbook",
        data={
            "name": "<b>Eve</b>",
            "website": "javascript:alert(1)",
            "message": "**hello** <img src=x onerror=alert(1)>",
        },
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    html = compact(r.text)
    assert "&lt;b&gt;Eve&lt;/b&gt;" in html  # plain str is text
    assert "<strong>hello</strong>" in html  # Markdown formatting kept
    assert "&lt;img" in html and "<img" not in html  # raw HTML escaped
    assert "javascript:" not in html  # URL policy
    page = c.get("/guestbook")
    assert "&lt;b&gt;Eve&lt;/b&gt;" in page.text
    assert 'class="announcement"' in page.text  # trusted Markup banner


def test_sse_page_and_feed(c):
    page = c.get("/sse")
    assert 'sse-connect="/api/sse"' in page.text
    assert "https://unpkg.com/htmx-ext-sse@2.2.3/dist/sse.min.js" in page.text
    feed = c.get("/api/sse?n=2")
    assert "text/event-stream" in feed.headers["content-type"]
    assert "event: message" in feed.text and "tick #1" in feed.text


def test_streamed_page(c):
    r = c.get("/stream")
    assert r.status_code == 200
    assert "row-49" in r.text


def test_health(c):
    assert c.get("/health").json() == {"ok": True, "app": "showcase"}


def test_posts_without_htmx_redirect_back(c):
    """Forms work without JavaScript: post/redirect/get."""
    r = c.post("/cart", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/cart"
    r = c.post(
        "/guestbook",
        data={"name": "Ann", "message": "hi"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"] == "/guestbook"


def test_nav_marks_current_page(c):
    html = compact(c.get("/shop").text)
    assert '<a aria-current="page" href="/shop">Shop</a>' in html
