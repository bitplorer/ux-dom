"""Live Chromium: a CSS value cannot add rules or declarations (#136).

Each vector is rendered with ux-dom tags and the page's CSSOM is read back:
``document.styleSheets`` must hold exactly the authored rules and selectors,
each declaring only the authored properties, and no ``//cdn.example`` URL may
appear in a rule or a ``style`` attribute. A vector that raises
``InvalidCSSValue`` emits nothing. Legitimate values must survive Chromium's
parser (no declaration dropped). Exact strings:
``tests/07_resilience/test_css_value_injection.py``.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from ux_dom.dom import div, script, style
from ux_dom.dom.src.csstags import CSSClass, Keyframes
from ux_dom.dom.src.utils.dom_util import InvalidCSSValue

from browser_gate import NODE, require_browser

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "raw_text_value_harness.mjs"
# Rules as Chromium parsed them, and each declared property with its value.
PROBE = script("""
const decls = (s) => Object.fromEntries([...s].map((p) => [p, s.getPropertyValue(p)]));
const rules = (list) => [...list].map((r) => ({
  sel: r.selectorText ?? r.keyText ?? r.name,
  decls: r.style ? decls(r.style) : {},
  rules: r.cssRules ? rules(r.cssRules) : [],
}));
__out.rules = [...document.styleSheets].flatMap((s) => rules(s.cssRules));
__out.attrs = [...document.querySelectorAll("[style]")].map((e) => decls(e.style));
""")


class btn(CSSClass):
    pass


class nxt(CSSClass):
    pass


class fade(Keyframes):
    pass


EVIL = "//cdn.example/x.png"
VALUES = {
    "close rule": "red} body{background:yellow",
    "extra declaration": f"red;background:url({EVIL})",
    "unclosed paren": "rgb(0,0,0",
    "comment": "red /*",
    "newline in string": '"a\n} body{background:yellow',
    "escaped url function": f"\\75rl({EVIL})",
}
# name: tree. Chromium must see the rule (``.btn`` or ``fade``), then ``.nxt``,
# declaring ``color`` only.
STRUCTURE = {
    **{
        f"rule {k}": lambda v=v: style(btn(color=v), nxt(color="blue"))
        for k, v in VALUES.items()
    },
    **{
        f"keyframes {k}": lambda v=v: style(fade(to={"color": v}), nxt(color="blue"))
        for k, v in VALUES.items()
    },
}
# name: tree. No ``cdn.example`` URL may reach the CSSOM.
URLS = {
    **{
        f"url in {prop}": lambda prop=prop: style(btn(**{prop: f"url({EVIL}), auto"}))
        for prop in ("cursor", "list_style_image", "border_image_source", "--icon")
    },
    "image-set": lambda: style(btn(background_image=f'image-set("{EVIL}" 1x)')),
    "style attribute url": lambda: div(style=f"width:1px;background-image:url({EVIL})"),
    "style attribute image-set": lambda: div(
        style=f"mask-image:image-set('{EVIL}' 1x)"
    ),
}
LEGIT = {
    "--brand": "#f00",
    "width": "calc(100% - 2px)",
    "font-family": "'Courier New', \"Segoe UI\", mono",
    "content": '"a;b}"',
    "background-image": 'url("https://cdn.example/a.png"), linear-gradient(red 0%, blue)',
    "cursor": "url(/c.png) 4 4, auto",
    "mask-image": 'image-set("a.png" 1x)',
    "grid-template-columns": "[full-start] minmax(0, 1fr) [full-end]",
}


def _rendered(vectors):
    """Each vector that renders; one that raises InvalidCSSValue emits nothing."""
    out = {}
    for name, make in vectors.items():
        try:
            out[name] = make().__render__(pretty=False)
        except InvalidCSSValue:
            pass
    return out


def _run(bodies):
    require_browser()
    probe = PROBE.__render__(pretty=False)
    proc = subprocess.run(
        [NODE, str(HARNESS)],
        cwd=str(ROOT),
        input=json.dumps([body + probe for body in bodies]),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return [page["out"] for page in json.loads(proc.stdout)]


def _flat(rules):
    for rule in rules:
        yield rule
        yield from _flat(rule["rules"])


class TestCssValueInjectionBrowser(unittest.TestCase):
    maxDiff = None

    def test_no_value_adds_rules_or_declarations(self):
        bodies = _rendered(STRUCTURE)
        injected = {}
        for name, out in zip(bodies, _run(bodies.values())):
            sels = [rule["sel"] for rule in out["rules"]]
            props = {p for rule in _flat(out["rules"]) for p in rule["decls"]}
            if sels not in ([".btn", ".nxt"], ["fade", ".nxt"]) or props - {"color"}:
                injected[name] = (sels, sorted(props))
        self.assertEqual(injected, {})

    def test_no_css_url_skips_the_allowlist(self):
        bodies = _rendered(URLS)
        leaked = {
            name: out
            for name, out in zip(bodies, _run(bodies.values()))
            if "cdn.example" in json.dumps(out)
        }
        self.assertEqual(leaked, {})

    def test_legitimate_values_survive_the_parser(self):
        attr = "; ".join(f"{k}: {v}" for k, v in LEGIT.items())
        (out,) = _run(
            [div(style(btn(**LEGIT)), div(style=attr)).__render__(pretty=False)]
        )
        self.assertEqual([rule["sel"] for rule in out["rules"]], [".btn"])
        for decls in (out["rules"][0]["decls"], out["attrs"][0]):
            # Chromium lists a shorthand by its longhands (``mask-image-*``).
            dropped = [p for p in LEGIT if not any(k.startswith(p) for k in decls)]
            self.assertEqual(dropped, [], decls)

    def test_ident_property_names_and_from_step_survive_the_parser(self):
        names = {"--x": "1", "--0": "2", "---": "3", "-webkit-line-clamp": "2"}
        keyframes = fade(from_={"opacity": 0}, to={"opacity": 1})
        (out,) = _run([style(btn(**names), keyframes).__render__(pretty=False)])
        self.assertEqual(set(out["rules"][0]["decls"]), set(names))
        self.assertEqual([r["sel"] for r in out["rules"][1]["rules"]], ["0%", "100%"])
