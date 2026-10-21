"""x_element.js refuses ws updates to URL attributes named by Python (#119).

The runtime cannot call the renderer's URL policy (#107), so it never lets a
WebSocket message set a URL-bearing attribute. Its name list must be exactly
the Python sets, or the two drift apart. Browser check:
``tests/06_browser/test_xelement_shadow_ws_browser.py``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ux_dom.dom.src.utils import dom_util

JS = Path(dom_util.__file__).resolve().parents[3] / "scripts" / "x_element.js"
LIST = re.compile(r"var WS_URL_ATTRS = (\[[^\]]*\]);")


def test_js_url_attribute_list_equals_python():
    (raw,) = LIST.findall(JS.read_text(encoding="utf-8"))
    js = json.loads(raw)
    python = (
        dom_util.URL_ATTRIBUTES
        | dom_util.SAME_ORIGIN_URL_ATTRIBUTES
        | dom_util._SRCSET_ATTRIBUTES
    )
    assert js == sorted(python)
    assert "xlink:href" in js
