"""F-04: parse→render must keep text and entities (no silent loss)."""

from __future__ import annotations

import html
import random
import re

import pytest

from ux_dom.dom.src.component import Fragment
from ux_dom.dom.src.html_string import defHTML


def _plain(out: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", out))


@pytest.mark.parametrize(
    "src,needles",
    [
        ("AT&T", ["AT", "T", "&amp;"]),
        ("Tom & Jerry", ["Tom", "Jerry", "&amp;"]),
        ("Tom &amp; Jerry", ["Tom", "Jerry", "&amp;"]),
        ("a&#39;b", ["a", "b", "&#39;"]),
        ("hello", ["hello"]),
    ],
)
def test_fragment_keeps_ampersands_and_entities(src, needles):
    out = str(Fragment(src))
    for n in needles:
        assert n in out, (src, n, out)
    plain = _plain(out)
    for token in re.findall(r"[A-Za-z]+", src.replace("amp", "")):
        if token.lower() in {"amp", "x"}:
            continue
        assert token in plain, (src, token, plain)


def test_defhtml_entity_nodes():
    out = "".join(n.__render__(pretty=False) for n in defHTML("Tom &amp; Jerry"))
    assert "&amp;" in out
    assert "Tom" in out and "Jerry" in out


def test_bare_ampersand_not_dropped():
    # HTMLParser previously ate AT&T down to AT
    assert "T" in _plain(str(Fragment("AT&T")))
    assert "&amp;" in str(Fragment("AT&T"))


def test_property_ampersand_roundtrip():
    rng = random.Random(42)
    alphabet = "abcXYZ019 &"  # no <> so the parser cannot swallow letters into tags
    for _ in range(200):
        s = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 40)))
        out = str(Fragment(s))
        plain = _plain(out)
        for ch in s:
            if ch.isalnum():
                assert ch in plain, (s, out, plain)


def test_entity_not_double_emitted():
    out = str(Fragment("Tom &amp; Jerry")).replace("\n", "")
    # One encoded amp, not "&amp;" plus bare "amp"
    assert out.count("&amp;") == 1
    assert "ampamp" not in out.replace("&amp;", "")
    plain = _plain(out)
    assert plain.count("&") == 1


def _flat(src: str) -> str:
    return "".join(n.__render__(pretty=False) for n in defHTML(src))


@pytest.mark.parametrize(
    "src,expected",
    [
        ("AT&T", "AT&amp;T"),
        ("a&", "a&amp;"),
        ("x &amp", "x &amp;"),
        ("&copy", "©"),
        ("&#x3C", "&#x3C;"),
        ("&#60", "&#60;"),
        ("<p>AT&T", "<p>AT&amp;T</p>"),
        ("<textarea>AT&T", "<textarea>AT&amp;T</textarea>"),
        ("<script>a&&b</script>AT&T", "AT&amp;T"),
    ],
)
def test_reference_at_end_of_input_is_kept(src: str, expected: str):
    """A ``&`` run that ends the string is text, not lost parser state.

    The tokenizer used to stop after ``feed`` and never ``close``, so a
    trailing ``&T`` stayed buffered and was dropped. Python 3.14.0's
    ``close`` also drops the ``&`` itself; the result must not depend on it.
    """
    assert _flat(src) == expected
