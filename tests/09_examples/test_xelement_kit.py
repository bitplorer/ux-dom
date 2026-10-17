"""examples/xelement_kit: XElement / htmx / Alpine pages on one Document.

Migrated from tests/02_document_plugins (TestXElementKit,
TestKitHypermediaPages), which loaded the kit through sys.path hacks.
"""

from __future__ import annotations

import pytest
from example_checks import assert_external_scripts_pinned, client

from ux_dom.runtime import XELEMENT_JS_URL

HTMX = "https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js"
ALPINE = "https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js"
PAGES = ("/", "/alpine", "/htmx", "/jinja", "/lightdom", "/shadowdom", "/slots", "/wc")


@pytest.fixture(scope="module")
def c():
    from examples.xelement_kit.main import app

    return client(app)


def test_health(c):
    assert c.get("/health").json() == {
        "ok": True,
        "app": "xelement_kit",
        "runtime": "x_element.js",
        "runtime_url": XELEMENT_JS_URL,
    }


def test_serves_x_element_js_from_the_package(c):
    js = c.get(XELEMENT_JS_URL)
    assert js.status_code == 200
    for needle in ("customElements.define", "x-tagname", "UxDom.XElement"):
        assert needle in js.text


@pytest.mark.parametrize("path", PAGES)
def test_every_page_loads_each_runtime_once_and_pinned(c, path):
    r = c.get(path)
    assert r.status_code == 200
    html = r.text
    assert html.count(f'src="{XELEMENT_JS_URL}"') == 1
    assert html.count("htmx.org@") == 1 and HTMX in html
    assert html.count("alpinejs@") == 1 and ALPINE in html
    assert_external_scripts_pinned(html)


def test_wc_page_definition_and_host(c):
    html = c.get("/wc").text
    for needle in ("x-tagname", "x-hello", "x-shadow-card"):
        assert needle in html


def test_alpine_page(c):
    html = c.get("/alpine").text
    for needle in ("x-tagname", "x-toggle", "x-counter", 'x-data="{ on: false }"'):
        assert needle in html


def test_htmx_demo_and_partial(c):
    demo = c.get("/htmx").text
    assert 'hx-get="/htmx/partial"' in demo
    first = c.get("/htmx/partial")
    second = c.get("/htmx/partial")
    assert first.status_code == 200
    assert "<html" not in first.text  # a fragment, not a page
    assert "x-hello" in first.text
    n1 = int(first.text.split('data-partial="')[1].split('"')[0])
    n2 = int(second.text.split('data-partial="')[1].split('"')[0])
    assert n2 == n1 + 1


def test_light_and_shadow_galleries(c):
    light = c.get("/lightdom").text
    assert "Light DOM" in light and "hello-light" in light and "x-tagname" in light
    shadow = c.get("/shadowdom").text
    assert "Shadow DOM" in shadow and "shadowroot" in shadow
    assert "profile-card" in shadow


def test_jinja_page(c):
    html = c.get("/jinja").text
    assert 'id="jinja-source"' in html and "Alpha" in html and "Gamma" in html


def test_slots_page(c):
    html = c.get("/slots").text
    assert "named-panel" in html and 'slot="header"' in html
    assert "multi-slot" in html
