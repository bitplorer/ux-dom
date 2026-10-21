"""Attack strings from the sanitizer PRs, as input to the string sanitizer.

Gathered from the tests that lock each fix (#32, #55, #85, #91, #97, #98,
#107, #113, #123, #125), not copied, so a vector added there is tested here too. Tree
corpora are rendered to the markup an attacker could send as a string. Used by
the sanitized-stream tests (#121).
"""

from __future__ import annotations

import importlib
import random


def _module(name: str):
    return importlib.import_module(f"tests.{name}")


def _param(func, argname: str) -> list:
    """The values of one ``@pytest.mark.parametrize`` argument of ``func``."""
    for mark in getattr(func, "pytestmark", []):
        names = mark.args[0] if mark.name == "parametrize" else ""
        if not isinstance(names, str):
            names = ",".join(names)
        if names.replace(" ", "") == argname:
            return list(mark.args[1])
    raise LookupError(f"{func.__name__} has no parametrize({argname!r})")


def _render(node) -> str:
    return node.__render__(pretty=False)


def _pr32() -> list[str]:
    parse = _module("07_resilience.test_html_parse_sanitizer")
    allow = _module("07_resilience.test_html_allowlist")
    mxss = _module("07_resilience.test_html_string_mxss")
    out = list(parse.ATTACKS) + [html for html, _ in parse.SAFE]
    out += list(allow.REVIEW_PAYLOADS) + [allow.PAGE]
    out += [mxss.NOSCRIPT_COMMENT, mxss.HOSTILE_DOCUMENT]
    out += list(mxss.DANGEROUS_CHILDREN)
    out += _param(mxss.test_comments_are_dropped, "src")
    out += _param(mxss.test_document_style_with_markup_is_refused, "src")
    out += [
        f'<{tag}><p title="</{tag}><img src=x onerror=alert(1)>">t</p></{tag}><b>ok</b>'
        for tag in _param(
            mxss.test_raw_text_elements_are_dropped_with_their_content, "tag"
        )
    ]
    out += [
        src
        for src, _ in _param(
            mxss.test_dangerous_scheme_is_dropped_from_parsed_attributes, "src,attr"
        )
    ]
    return out


def _pr55() -> list[str]:
    return list(_module("07_resilience.test_raw_string_sinks").PAYLOADS)


def _pr85() -> list[str]:
    m = _module("07_resilience.test_foreign_content_raw_text")
    payloads = _param(m.test_foreign_body_is_one_cdata_section, "payload")
    return [
        _render(wrap(kind(payload)))
        for wrap in [*m.FOREIGN.values(), *m.HTML.values()]
        for kind in (m.style, m.script)
        for payload in payloads
    ]


def _pr91() -> list[str]:
    m = _module("07_resilience.test_text_state_parents")
    out = []
    for name in [*m.RCDATA, *m.RAWTEXT]:
        for child in m.CHILDREN.values():
            out.append(f"<div><{name}>{_render(child(name))}</{name}></div>")
    for wrap in m.FOREIGN.values():
        for name in ("textarea", "xmp"):
            out.append(
                _render(wrap(m.div())).replace(
                    "<div></div>", f"<{name}><style></{name}>{m.IMG}</style></{name}>"
                )
            )
    return out


def _pr97() -> list[str]:
    m = _module("01_core.test_parse_whitespace")
    return list(m.SOURCES) + [source for source, _ in m.SANITIZED]


def _pr98() -> list[str]:
    m = _module("07_resilience.test_foreign_breakout")
    els = [m.style(m.CSS), m.style("x</style>" + m.IMG), m.style(m.IMG)]
    return [
        _render(wrap(el))
        for wrap in [*m.HTML.values(), *m.FOREIGN.values()]
        for el in els
    ]


def _pr107() -> list[str]:
    m = _module("07_resilience.test_svg_animation_urls")
    out = []
    for value in [*m.EVIL, *m.PAYLOADS]:
        quoted = str(value).replace('"', "&quot;")
        for tag, attr in m.ANIMATION_CHECKED:
            out.append(
                f'<svg><a><{tag} attributeName="href" {attr}="{quoted}" dur="0.05s" '
                f'fill="freeze"/><rect width="50" height="50"/></a></svg>'
            )
        for tag, attr in m.URL_CHECKED:
            out.append(f'<{tag} {attr}="{quoted}">x</{tag}>')
    return out


def _pr113() -> list[str]:
    m = _module("07_resilience.test_html_svg_names")
    return [
        f"<svg><{spell(name)} id=x onload=alert(1)><rect></rect>"
        f"<script>alert(1)</script></{spell(name)}><circle></circle></svg>"
        for name in [*m.KEPT, *m.DROPPED]
        for spell in m.SPELLINGS
    ]


# Pieces that open and end every construct the tokenizer and its reference
# pass know, so random joins and splits land in all of them.
TOKENS = [
    "<!--",
    "-->",
    "--!>",
    "<!-->",
    "<!--->",
    "-",
    "!",
    "<a",
    "<p",
    "<b>",
    "</b>",
    " title=",
    " href=",
    '"',
    "'",
    ">",
    "</p>",
    "</a>",
    "<script>",
    "</script>",
    "<style>",
    "</style>",
    "<style/>",
    "<STYLE ",
    "<ſtyle>",
    "<![CDATA[",
    "]]>",
    "<!",
    "<?",
    "<!DOCTYPE",
    "<",
    "</",
    "/>",
    "x",
    " ",
    "\t",
    "\n",
    "\r",
    ";",
    "=",
    "&",
    "&amp;",
    "&#62",
    "&#x3c",
    "&#",
    "&notin;",
    "&not",
    "é",
    "<svg>",
    "</svg>",
    "<math>",
    "<textarea>",
    "</textarea",
    "<title>",
    "</title>",
    "<xmp>",
    "</xmp>",
    "<plaintext>",
    "<template>",
    "</template>",
    "<noscript>",
    "</noscript>",
    "<img",
    " onerror=alert(1)",
    "javascript:alert(1)",
    "<br>",
    "<li>",
    # Implied end tags and breakouts (#125): a cut must never fall inside an
    # element a later tag closes implicitly.
    "<ul>",
    "</li>",
    "<dt>",
    "<dd>",
    "<select>",
    "<option>",
    "<table>",
    "<tr>",
    "<td>",
    "<ruby>",
    "<rt>",
    "<form>",
    "</form>",
    "</br>",
    "<h1>",
    "<div/>",
    "<button>",
    "<desc>",
    "<colgroup>",
]


def _pr123() -> list[str]:
    """Seeded joins of ``TOKENS``, as the stream test joins them."""
    rng = random.Random(123)
    return ["".join(rng.choices(TOKENS, k=rng.randint(2, 14))) for _ in range(300)]


def _pr125() -> list[str]:
    """Implied end tags and breakouts around the attack payloads."""
    m = _module("07_resilience.test_html_tree_construction")
    payloads = [
        "<img src=x onerror=alert(1)>",
        "<script>alert(1)</script>",
        "<a href=javascript:alert(1)>a</a>",
        "<style><img src=x onerror=alert(1)></style>",
        "<noscript><p title='</noscript><img src=x onerror=alert(1)>'></noscript>",
    ]
    out = [src for src, _ in m.IMPLIED]
    out += [src + payload for src, _ in m.IMPLIED for payload in payloads[:2]]
    for payload in payloads:
        out += [
            f"<p>a<svg><p>{payload}",
            f"<svg><g><li>{payload}</g></svg>",
            f"<table><td>a<svg><td>{payload}</table>",
            f"<select><option>a<option>{payload}</select>",
            f"<form><div>a</form>{payload}",
            f"<div/>{payload}",
            "<b>" * 600 + payload,
            "<li>" * 600 + payload,
        ]
    return out


CORPORA = {
    "#32": _pr32,
    "#55": _pr55,
    "#85": _pr85,
    "#91": _pr91,
    "#97": _pr97,
    "#98": _pr98,
    "#107": _pr107,
    "#113": _pr113,
    "#123": _pr123,
    "#125": _pr125,
}


def corpus() -> list[tuple[str, str]]:
    """``(source PR, attack string)``, deduplicated, in a stable order."""
    seen: set[str] = set()
    out = []
    for pr, build in CORPORA.items():
        for text in build():
            if text not in seen:
                seen.add(text)
                out.append((pr, text))
    return out
