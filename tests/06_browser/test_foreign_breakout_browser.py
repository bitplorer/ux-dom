"""Live Chromium: the renderer's namespace model is the parser's (#92).

In foreign content a breakout start tag (``<p>``, ``<div>``, ``<img>`` …, and
``<font>`` with ``color`` / ``face`` / ``size``) pops the parser back to HTML,
for its descendants and for every later sibling (HTML spec §13.2.6.5). The
model (``htmltags._parsed_namespace``) must give each element the
``namespaceURI`` Chromium gives it, so a ``style`` / ``script`` after a
breakout is raw text (its CSS / JS works) and one in foreign content is CDATA.

Where the tree cannot tell whether the HTML rules closed an element early, the
model keeps the foreign answer: it may say foreign where Chromium says HTML,
never the reverse (``CONSERVATIVE``). Exact strings:
``tests/07_resilience/test_foreign_breakout.py``.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import unittest
from pathlib import Path

from ux_dom import Component
from ux_dom.dom import a, br, div, img, p, script, span, style
from ux_dom.dom.src.ext import PlaceholderTag, Tags, _element_name
from ux_dom.dom.src.htmltags import _BREAKOUT_ELEMENTS, _parsed_namespace
from ux_dom.dom.src.svgtags import circle, desc, foreignObject, g, rect, svg, svg_tag
from ux_dom.dom.src.svgtags import title as svg_title

from browser_gate import NODE, require_browser

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "raw_text_value_harness.mjs"
URI = {
    "html": "http://www.w3.org/1999/xhtml",
    "svg": "http://www.w3.org/2000/svg",
    "math": "http://www.w3.org/1998/Math/MathML",
}


def _tag(name, base=Tags, **kw):
    return type(name.replace("-", "_"), (base,), {"tagname": name, **kw})


svg_a = _tag("a", svg_tag)
math, mi, mo, mglyph = _tag("math"), _tag("mi"), _tag("mo"), _tag("mglyph")
annotation_xml = _tag("annotation-xml")
font = _tag("font")


def _component(el):
    class Wrap(Component):
        def render(self):
            return el

    return Wrap()


def _shapes():
    """Tree shapes: every breakout name as a descendant, a sibling, below a
    nested ``svg`` / integration point, and in MathML."""
    shapes = {}
    for name in sorted(_BREAKOUT_ELEMENTS - {"head", "body"}):
        E = _tag(name)
        shapes |= {
            f"svg>{name}>style": lambda E=E: svg(E(style("a{}"), rect())),
            f"svg>[{name},script,…]": lambda E=E: svg(
                E(), script("1"), rect(), g(circle())
            ),
            f"svg>g>{name}": lambda E=E: svg(g(E(), rect()), circle(), svg(rect())),
            f"math>[{name},mi,…]": lambda E=E: math(E(), mi(), mglyph(), style("a{}")),
            f"svg>foreignObject>svg>{name}": lambda E=E: svg(
                foreignObject(svg(E(), rect()), rect()), rect()
            ),
            f"svg>desc>svg>g>{name}": lambda E=E: svg(
                desc(svg(g(E(), rect()), rect()), rect()), rect()
            ),
            f"math>annotation-xml>svg>{name}": lambda E=E: math(
                annotation_xml(svg(E()), style("a{}"), mglyph()), mi()
            ),
            f"math>annotation-xml[html]>svg>{name}": lambda E=E: math(
                annotation_xml(
                    svg(E()), style("a{}"), mglyph(), encoding="text/html"
                ),
                mi(),
            ),
        }
    for name in ("head", "body"):  # ignored in <body>: their children stay
        E = _tag(name)
        shapes[f"svg>{name}"] = lambda E=E: svg(
            E(rect(), style("a{}")), circle(), style("b{}")
        )
    for attr in ("color", "face", "size", "COLOR", "class"):
        shapes[f"svg>font[{attr}]"] = lambda attr=attr: svg(
            font(rect(), **{attr: "1"}), rect(), style("a{}")
        )
    shapes |= {
        "svg>font": lambda: svg(font(rect()), rect()),
        "svg>font[color=False]": lambda: svg(font(rect(), color=False), rect()),
        "svg>Component>p": lambda: svg(_component(p()), style("a{}"), rect()),
        "svg>PlaceholderTag>div": lambda: svg(PlaceholderTag(div(), rect()), script("1")),
        "div>[svg>p, style, svg>style]": lambda: div(
            svg(p(), rect()), style("a{}"), svg(rect(), style("b{}"))
        ),
        "svg>p>svg>style": lambda: svg(p(svg(style("a{}"), rect())), rect()),
        "svg>foreignObject>p": lambda: svg(
            foreignObject(p(), style("a{}")), rect(), style("b{}")
        ),
        "svg>open animateTransform": lambda: svg(
            _tag("animateTransform", svg_tag, is_single=True)(), rect(), style("a{}")
        ),
        "math>mi>open mglyph": lambda: math(
            mi(_tag("mglyph", is_single=True)(), style("a{}"))
        ),
        "svg>a>foreignObject>a>a": lambda: svg(
            svg_a(foreignObject(a(a()), style("a{}"))), rect()
        ),
        "math>mi>img>mglyph": lambda: math(mi(img(mglyph(style("a{}"))))),
        "math>mi>p>[div,mglyph]": lambda: math(mi(p(div(), mglyph(style("a{}"))))),
        "div>table>svg>p": lambda: div(_tag("table")(svg(p(style("a{}")), rect()))),
    }
    # #128: an HTML element no rule closes early is still open at its end tag,
    # which must not pop the integration point of the same name below it.
    shapes |= {
        "svg>desc>[desc,script]": lambda: svg(desc(desc(), script("1")), rect()),
        "math>mi>[mi,script]": lambda: math(mi(mi(), script("1")), mglyph()),
        "math>mtext>[mtext,script]": lambda: math(
            _tag("mtext")(_tag("mtext")(), script("1")), mi()
        ),
        "svg>g>desc>[g,script]": lambda: svg(g(desc(g(), script("1"))), rect()),
    }
    for name in ("div", "span", "ul"):
        E = _tag(name)
        shapes[f"math>mi>mglyph>{name}"] = lambda E=E: math(
            mi(mglyph(E(mglyph(style("a{}")))))
        )
    return shapes


# The model says MathML, Chromium HTML: an HTML element between mi and mglyph
# that the parser may close early (``math>mi>p>[div,mglyph]``), and the tree
# does not say whether it did. Foreign is the safe answer.
CONSERVATIVE = {
    f"math>mi>mglyph>{name}": lambda E=_tag(name): math(
        mi(mglyph(E(mglyph(style("a{}")))))
    )
    for name in ("b", "p", "table")
}

CSS = ".c::before { content: 'a > b & c'; }"
JS = "__out.v = (1 < 2 && 3 > 2) ? '</p> & <b>' : 0;"
# Legitimate CSS / JS after a breakout: raw text in Chromium.
LEGIT = {
    "svg>p>style": lambda: div(svg(p(style(CSS))), span(className="probe c")),
    "svg>[div,style]": lambda: div(svg(div(), style(CSS)), span(className="probe c")),
    "svg>g>[p],style": lambda: div(svg(g(p()), style(CSS)), span(className="probe c")),
    "svg>font[color]>style": lambda: div(
        svg(font(style(CSS), color="red")), span(className="probe c")
    ),
    "math>[br,style]": lambda: div(math(br(), style(CSS)), span(className="probe c")),
    "svg>p>script": lambda: svg(p(script(JS))),
    "svg>[div,script]": lambda: svg(div(), script(JS)),
    "svg>[img,script]": lambda: svg(img(), script(JS)),
    "math>mi>mglyph>[span,script]": lambda: math(mi(mglyph(span(), script(JS)))),
    # Still foreign: a nested svg after the breakout opens SVG again.
    "svg>[p,svg>style]": lambda: div(
        svg(p(), svg(style(f"<![CDATA[{CSS}]]>"))), span(className="probe c")
    ),
    "svg>[p,svg>script]": lambda: svg(p(), svg(script(JS))),
}

PWN = "<img src=x onerror=__out.pwn=1>"
# #85's attack corpus plus the breakout and early-close shapes.
CONTEXTS = {
    "svg": lambda el: svg(el),
    "svg>g": lambda el: svg(g(el)),
    "math": lambda el: math(el),
    "math>mi>mglyph": lambda el: math(mi(mglyph(el))),
    "math>annotation-xml": lambda el: math(annotation_xml(el)),
    "svg>foreignObject>svg": lambda el: svg(foreignObject(svg(el))),
    "svg>p": lambda el: svg(p(el)),
    "svg>[div,el]": lambda el: svg(div(), el),
    "svg>[g>p,el]": lambda el: svg(g(p()), el),
    "svg>foreignObject>[svg>p,el]": lambda el: svg(foreignObject(svg(p()), el)),
    "svg>desc>[svg>g>p],el": lambda el: svg(desc(svg(g(p()))), el),
    "math>mi>mglyph>[p>mglyph>el]": lambda el: math(mi(mglyph(p(mglyph(el))))),
    "math>mi>mglyph>[img,mglyph>el]": lambda el: math(mi(mglyph(img(), mglyph(el)))),
    "math>mi>img>mglyph": lambda el: math(mi(img(mglyph(el)))),
    "math>mi>p>[div,mglyph>el]": lambda el: math(mi(p(div(), mglyph(el)))),
    "math>mi>open mglyph": lambda el: math(mi(_tag("mglyph", is_single=True)(), el)),
    "svg>a>foreignObject>[a>a,el]": lambda el: svg(svg_a(foreignObject(a(a()), el))),
    "svg>font[color]>[svg>g,el]": lambda el: svg(font(svg(g()), el, color="red")),
    "svg>[a>[title>title,p],el]": lambda el: svg(svg_a(svg_title(svg_title()), p()), el),
}
PAYLOADS = [
    PWN,
    "</style>" + PWN,
    "</script>" + PWN,
    "]]>" + PWN,
    "x]]]]>" + PWN,
    "<![CDATA[x]]>" + PWN,
    "<![CDATA[]]>" + PWN + "<![CDATA[]]>",
]


def _async(node, **kw):
    async def go():
        return "".join([t async for t in node.__async_render__(**kw)])

    return asyncio.run(go())


def _renders(node):
    return [
        node.__render__(pretty=False),
        node.__render__(pretty=True),
        _async(node, pretty=False),
        _async(node, pretty=True),
    ]


def _browser(pages):
    require_browser()
    proc = subprocess.run(
        [NODE, str(HARNESS)],
        cwd=str(ROOT),
        input=json.dumps(pages),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout)


def _with_ids(root):
    """``root`` rendered with an ``id`` on each element, and the model's
    namespace URI per ``id``."""
    elements = []

    def collect(node):
        if not isinstance(node, Tags):
            return
        name = _element_name(node)
        if name not in (None, "head", "body"):  # the parser drops these two
            elements.append(node)
        if name not in ("style", "script"):
            for child in node.children:
                collect(child)

    collect(root)
    for i, el in enumerate(elements):
        el.attributes["id"] = f"e{i}"
    model = {f"e{i}": URI[_parsed_namespace(el)] for i, el in enumerate(elements)}
    return root.__render__(pretty=False), model


class TestForeignBreakoutBrowser(unittest.TestCase):
    def _compare(self, shapes):
        names = list(shapes)
        built = [_with_ids(shapes[n]()) for n in names]
        results = _browser([html for html, _ in built])
        return names, built, results

    def test_model_namespace_is_chromium_namespace(self):
        names, built, results = self._compare(_shapes())
        for name, (html, model), got in zip(names, built, results):
            with self.subTest(shape=name):
                self.assertEqual(got["ns"], model, html)

    def test_model_is_foreign_where_unsure(self):
        names, built, results = self._compare(CONSERVATIVE)
        for name, (html, model), got in zip(names, built, results):
            with self.subTest(shape=name):
                for id_, uri in got["ns"].items():
                    if model[id_] == URI["html"]:
                        self.assertEqual(uri, URI["html"], html)
                self.assertNotEqual(got["ns"], model, "now exact: move to _shapes")

    def test_css_and_js_after_breakout_work(self):
        names = list(LEGIT)
        pages = [r for n in names for r in _renders(LEGIT[n]())]
        results = _browser(pages)
        for i, name in enumerate(names):
            for got in results[4 * i : 4 * i + 4]:
                with self.subTest(page=name):
                    if "probe" in pages[4 * i]:
                        self.assertEqual(got["before"], ['"a > b & c"'], pages[4 * i])
                    else:
                        self.assertEqual(got["out"], {"v": "</p> & <b>"}, pages[4 * i])

    def test_attack_corpus_runs_nothing(self):
        pages = [
            r
            for where in CONTEXTS.values()
            for kind in (style, script)
            for payload in PAYLOADS
            for r in _renders(where(kind(payload)))
        ]
        results = _browser(pages)
        ran = [page for page, got in zip(pages, results) if got["out"].get("pwn")]
        self.assertEqual(ran, [], f"{len(ran)} of {len(pages)} pages ran script")


if __name__ == "__main__":
    unittest.main()
