"""Round-2 re-review blockers: check-then-use and shared unescape state."""

from __future__ import annotations

from html.parser import HTMLParser

from ux_dom.alpinejs import DataSet
from ux_dom.dom import a, div, iframe, span
from ux_dom.dom.src.utils.dom_util import UNSAFE_URL, safe_attr_value


def _starttags(html: str) -> list[tuple[str, dict]]:
    found: list[tuple[str, dict]] = []

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            found.append((tag, dict(attrs)))

    P().feed(html)
    return found


class _Flip:
    """str() is safe the first time and a script URL after that."""

    def __init__(self) -> None:
        self.calls = 0

    def __str__(self) -> str:
        self.calls += 1
        return "/ok" if self.calls == 1 else "javascript:alert(1)"


class _FlipHtml:
    def __init__(self) -> None:
        self.calls = 0

    def __html__(self) -> str:
        self.calls += 1
        return "<p>ok</p>" if self.calls == 1 else "<script>alert(1)</script>"


# --- Blocker 1: the checked text is the text that renders -----------------


def test_helper_returns_the_checked_text():
    out = safe_attr_value("href", _Flip())
    assert out == "/ok"
    assert isinstance(out, str)


def test_flipping_str_cannot_reach_render():
    html = a("x", href=_Flip()).__render__(pretty=False)
    assert "javascript" not in html.lower()
    assert _starttags(html)[0][1]["href"] in ("/ok", UNSAFE_URL)


def test_flipping_html_opt_in_cannot_reach_render():
    html = iframe(srcdoc=_FlipHtml()).__render__(pretty=False)
    assert "script" not in html.lower()


# --- Blocker 2: unescape opt-out is per instance, and never raw " or & ----


def test_unescape_marker_does_not_leak_to_other_tags():
    a_tag, b_tag = span(), span()
    assert a_tag.safe_attributes is not b_tag.safe_attributes
    a_tag.safe_attributes["class"] = False
    assert b_tag.safe_attributes.get("class", True) is True


def test_dataset_does_not_disable_escaping_globally():
    with DataSet():
        div("a", className="x", x_data="{'a': 1}")
    payload = '" onmouseover="alert(1)'
    html = span("t", class_=payload).__render__(pretty=False)
    tags = _starttags(html)
    assert tags[0][1] == {"class": payload}


def test_opt_out_path_cannot_break_out_of_attribute():
    tag = span("t", **{"class": '" onmouseover="alert(1)', "@click": 'a && b" x="1'})
    tag.safe_attributes["class"] = False
    tag.safe_attributes["@click"] = False
    html = tag.__render__(pretty=False)
    tags = _starttags(html)
    assert set(tags[0][1]) == {"class", "@click"}
    assert tags[0][1]["class"] == '" onmouseover="alert(1)'
    assert tags[0][1]["@click"] == 'a && b" x="1'


def test_opt_out_srcdoc_cannot_break_out():
    class _H:
        def __html__(self):
            return '"><script>alert(1)</script>'

    tag = iframe(srcdoc=_H())
    tag.safe_attributes["srcdoc"] = False
    tags = _starttags(tag.__render__(pretty=False))
    assert [t for t, _ in tags] == ["iframe"]
    assert tags[0][1]["srcdoc"] == '"><script>alert(1)</script>'


def test_opt_out_keeps_alpine_quotes_readable():
    # The opt-out exists so Alpine JSON / handlers keep ' and > as-is.
    tag = div(x_data="{'a': 1}", **{"@click": "n > 0 && go('x')"})
    tag.safe_attributes["x-data"] = False
    tag.safe_attributes["@click"] = False
    html = tag.__render__(pretty=False)
    assert "x-data=\"{'a': 1}\"" in html
    assert "n > 0 &amp;&amp; go('x')" in html
