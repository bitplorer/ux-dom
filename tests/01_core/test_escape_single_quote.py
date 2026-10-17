"""escape(quote=True) must neutralise both quote characters, like html.escape."""
from ux_dom.dom import div
from ux_dom.dom.src.utils.dom_util import escape


def test_escape_quotes_single_quote():
    assert escape("a'b", quote=True) == "a&#39;b"


def test_escape_without_quote_keeps_single_quote():
    assert escape("a'b", quote=False) == "a'b"


def test_attribute_single_quote_is_escaped():
    html = div(title="x' onmouseover='alert(1)").__render__()
    assert "'" not in html.split("title=", 1)[1].split(">", 1)[0].strip('"')
    assert "&#39;" in html


def test_escape_round_trips_through_unescape():
    # Oracle is the stdlib decoder (browsers decode the same entities).
    from html import unescape

    assert unescape(escape("it's <b>&\"")) == "it's <b>&\""
