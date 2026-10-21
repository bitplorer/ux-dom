"""Live Chromium: SVG animation values cannot set a ``javascript:`` URL (#86).

``<animate attributeName="href" to="javascript:…">`` inside an SVG ``<a>``
ran script on click, as did a list or dict ``values`` whose JSON text SMIL
splits on ``;``. Every vector below is built with ux-dom tags, rendered,
loaded and clicked; no page may call ``hit()``. Legitimate SMIL animations
(opacity, transform, colour, motion, fragment ``href``) must still animate.
Exact strings: ``tests/07_resilience/test_svg_animation_urls.py``.
Evidence: https://github.com/bitplorer/ux-dom/issues/86.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from markupsafe import Markup

from ux_dom.dom.src.svgtags import (
    animate,
    animateMotion,
    animateTransform,
    circle,
    defs,
    rect,
    svg,
    svg_tag,
)

from ux_dom.dom.src.utils.dom_util import lazy

from browser_gate import NODE, require_browser

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "url_click_harness.mjs"


def _svg_el(name):
    return type(name, (svg_tag,), {"tagname": name})


svg_a, svg_set, use = _svg_el("a"), _svg_el("set"), _svg_el("use")
ANIMATIONS = {
    "animate": animate,
    "set": svg_set,
    "ANIMATE": _svg_el("ANIMATE"),
    "animateMotion": animateMotion,
    "animateTransform": animateTransform,
}
OBFUSCATIONS = {
    "plain": "javascript:hit()",
    "case": "JaVaScRiPt:hit()",
    "lead-space": "  javascript:hit()",
    "lead-ctrl": "\x01javascript:hit()",
    "tab": "java\tscript:hit()",
    "lf": "java\nscript:hit()",
    "cr": "java\rscript:hit()",
    "Markup": Markup("javascript:hit()"),
}
TIMING = {"dur": "0.05s", "fill": "freeze"}
SPLIT = "#x;javascript:hit()//"  # SMIL splits on ``;``; ``//`` comments out the rest


class _Str:
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


# Every type a value can arrive as; the check must see the text that renders.
WRAPPERS = {
    "str": lambda p: p,
    "Markup": Markup,
    "list": lambda p: [p],
    "dict": lambda p: {"a": p},
    "tuple": lambda p: (p,),
    "__str__": _Str,
    "lazy": lambda p: lazy(lambda: p),
}


def _link(anim, target, **values):
    """A clickable SVG ``<a>`` linking ``#safe`` through ``target``, animated."""
    return svg(
        svg_a(
            rect(width="80", height="40"),
            ANIMATIONS[anim](attributeName=target, **values, **TIMING),
            **{target: "#safe"},
        ),
        width="100",
        height="50",
    )


def _vectors():
    out = {}
    for anim in ("animate", "set"):
        for obf, url in OBFUSCATIONS.items():
            out[f"{anim} href to {obf}"] = _link(anim, "href", to=url)
        for target in ("href", "xlink:href"):
            js = OBFUSCATIONS["plain"]
            out[f"{anim} {target} to"] = _link(anim, target, to=js)
            out[f"{anim} {target} from"] = _link(anim, target, _from=js, to=js)
            out[f"{anim} {target} by"] = _link(anim, target, by=js)
            out[f"{anim} {target} values"] = _link(anim, target, values=js)
            out[f"{anim} {target} values list"] = _link(
                anim, target, values="#a;" + js
            )
    for anim in ("animate", "set", "ANIMATE"):
        for name, wrap in WRAPPERS.items():
            for attr in ("to", "values"):
                out[f"{anim} href {attr} {name}"] = _link(anim, "href", **{attr: wrap(SPLIT)})
    for anim in ("animateMotion", "animateTransform"):
        out[f"{anim} href to"] = _link(anim, "href", to=OBFUSCATIONS["plain"])
    return out


# name: (tree, probe, expected probe value)
LEGIT = {
    "opacity": (
        svg(rect(animate(attributeName="opacity", to="0.25", **TIMING), id="r")),
        "getComputedStyle(document.getElementById('r')).opacity",
        "0.25",
    ),
    "opacity values": (
        svg(rect(animate(attributeName="opacity", values="1;0.5;0", **TIMING), id="r")),
        "getComputedStyle(document.getElementById('r')).opacity",
        "0",
    ),
    "colour": (
        svg(rect(animate(attributeName="fill", _from="red", to="rgb(0, 128, 0)", **TIMING), id="r")),
        "getComputedStyle(document.getElementById('r')).fill",
        "rgb(0, 128, 0)",
    ),
    "transform": (
        svg(
            rect(
                animateTransform(
                    attributeName="transform", type="translate", _from="0 0", to="10 20", **TIMING
                ),
                id="r",
            )
        ),
        "(m => [m.e, m.f])(document.getElementById('r').getCTM())",
        [10, 20],
    ),
    "motion values": (
        svg(rect(animateMotion(values="0,0;30,5", **TIMING), id="r", width="1", height="1")),
        "(m => [m.e, m.f])(document.getElementById('r').getCTM())",
        [30, 5],
    ),
    "set fragment href": (
        svg(svg_a(rect(width="8", height="8"), svg_set(attributeName="href", to="#b", **TIMING), id="l", href="#a")),
        "document.getElementById('l').href.animVal",
        "#b",
    ),
    "animate fragment href values": (
        svg(
            defs(circle(id="c1", r="1"), circle(id="c2", r="2")),
            use(animate(attributeName="href", values="#c1;#c2", **TIMING), id="u", href="#c1"),
        ),
        "document.getElementById('u').href.animVal",
        "#c2",
    ),
}


def _run(pages):
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


class TestSvgAnimationUrlBrowser(unittest.TestCase):
    maxDiff = None

    def test_no_animation_vector_runs_script(self):
        vectors = _vectors()
        pages = [{"html": tree.__render__(pretty=False), "probe": None} for tree in vectors.values()]
        results = _run(pages)
        ran = {name: r["hits"] for name, r in zip(vectors, results) if r["hits"]}
        self.assertEqual(ran, {})

    def test_legitimate_animations_still_animate(self):
        pages = [{"html": tree.__render__(pretty=False), "probe": probe} for tree, probe, _ in LEGIT.values()]
        results = _run(pages)
        for (name, (_, _, want)), got in zip(LEGIT.items(), results):
            with self.subTest(animation=name):
                self.assertEqual(got["probe"], want)
                self.assertEqual(got["hits"], 0)


if __name__ == "__main__":
    unittest.main()
