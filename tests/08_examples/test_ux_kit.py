"""examples/ux_kit: the ux_dom.ui gallery on a Document.

Migrated from tests/02_document_plugins/test_ui_kit.py::TestGalleryApp and
tests/04_production/test_production_stability.py::TestUiGallery. The channel
section is gone from the gallery (its actions had no handler and no host);
the channel pattern is covered by tests/08_examples/test_ux_channel_counter.py.
"""

from __future__ import annotations

import pytest
from example_checks import assert_external_scripts_pinned, client, compact


@pytest.fixture(scope="module")
def c():
    from examples.ux_kit.main import app

    return client(app)


def test_gallery_is_a_full_document(c):
    r = c.get("/")
    assert r.status_code == 200
    assert r.text.lower().startswith("<!doctype html>")
    html = compact(r.text)
    assert "<title>UI Kit · UxDom</title>" in html
    assert "UxDom UI kit" in html
    assert "bg-stone-900" in html  # ux_dom.ui tokens rendered
    assert "https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js" in html
    assert_external_scripts_pinned(r.text)


def test_gallery_renders_every_section(c):
    html = compact(c.get("/").text)
    for heading in (
        "Buttons",
        "Form controls",
        "Surfaces",
        "Table",
        "Tabs",
        "Dialog",
        "Carousel",
        "Toast",
        "Chart (SVG)",
        "Avatar / Skeleton / Separator",
    ):
        assert f">{heading}</h2>" in html, heading


def test_no_dead_channel_actions(c):
    html = c.get("/").text
    assert "data-channel-action" not in html
    assert "Demo.ping" not in html
    assert "x_element.js" not in html  # ux_dom.ui needs no client runtime


def test_state_is_a_render_argument(c):
    html = compact(c.get("/?tab=b&slide=1").text)
    assert 'aria-selected="true"' in html
    assert "Change your password here." in html
    assert "2 / 2" in html


def test_htmx_button_swaps_a_toast(c):
    page = c.get("/").text
    assert 'hx-post="/toast"' in page
    r = c.post("/toast", headers={"HX-Request": "true"})
    assert r.status_code == 200
    assert "<html" not in r.text
    assert "Saved at" in r.text


def test_health(c):
    assert c.get("/health").json() == {"ok": True, "app": "ux_kit"}
