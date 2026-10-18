"""F-21: SNIPPETS Fragment example must run."""

from __future__ import annotations


def test_fragment_classname_snippet():
    from ux_dom import Fragment
    from ux_dom.dom import span

    tree = Fragment(span("A"), span("B"), className="row")
    html = tree.__render__()
    assert 'class="row"' in html
    assert "A" in html and "B" in html
