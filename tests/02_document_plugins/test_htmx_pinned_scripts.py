"""HTMX scripts are exact files with SRI (review M3)."""

from __future__ import annotations

import re

import pytest

from ux_dom.plugins.control.htmx import CDN_SCRIPT_URLS, PINNED_SCRIPTS, HtmxControl


def tags(control) -> list[str]:
    return [str(x) for x in control.document_body()]


@pytest.mark.parametrize("version", sorted(PINNED_SCRIPTS))
@pytest.mark.parametrize("sse", [False, True])
def test_every_script_is_pinned_with_integrity(version, sse):
    out = tags(HtmxControl(version=version, sse=sse))
    assert len(out) == (3 if sse else 2)
    for tag in out:
        src = re.search(r'src="([^"]+)"', tag).group(1)
        assert src in CDN_SCRIPT_URLS
        assert re.search(r"@\d+\.\d+\.\d+/", src), src  # exact version, no redirect
        assert re.search(r'integrity="sha384-[A-Za-z0-9+/=]{64}"', tag)
        assert 'crossorigin="anonymous"' in tag


def test_sse_extension_matches_htmx_major():
    assert "htmx.org@1.9.12/dist/ext/sse.js" in "".join(tags(HtmxControl(sse=True)))
    assert "htmx-ext-sse@2.2.3" in "".join(tags(HtmxControl(version="2.0.4", sse=True)))


def test_unpinned_version_refused_unless_self_hosted():
    with pytest.raises(ValueError):
        HtmxControl(version="1.9.2")
    assert tags(HtmxControl(version="1.9.2", cdn=False)) == []
