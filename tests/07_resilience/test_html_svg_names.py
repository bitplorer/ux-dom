"""#104: the string sanitizer keeps camelCase SVG names it allows, with their case.

The tokenizer lowercases tag names, so the allowlist (lowercase) did not
match the gradient / clip / text-path elements and unwrapped them. They are
SVG geometry and paint like ``pattern`` / ``mask`` / ``stop`` (ADR 0002), so
they are kept. The HTML tree builder restores SVG case from the spec's
table (§13.2.6.5, "adjust SVG tag name"); the sanitizer uses the same table
to find the tag class, so ``<lineargradient>`` is written ``<linearGradient>``.
Every other name in the table stays dropped (animation, ``foreignObject``)
or unwrapped (filters, ``altGlyph`` …), in any case.

Chromium oracle: ``tests/06_browser/test_sanitizer_svg_browser.py``.
"""

from __future__ import annotations

import pytest

from ux_dom.dom.src.html_string import (
    _ALLOWED_TAGS,
    _DROP_TAGS,
    _SVG_TAG_NAMES,
    _sanitized_html,
)

# HTML spec §13.2.6.5, "adjust SVG tag name", as written there.
SPEC_TABLE = [
    "altGlyph",
    "altGlyphDef",
    "altGlyphItem",
    "animateColor",
    "animateMotion",
    "animateTransform",
    "clipPath",
    "feBlend",
    "feColorMatrix",
    "feComponentTransfer",
    "feComposite",
    "feConvolveMatrix",
    "feDiffuseLighting",
    "feDisplacementMap",
    "feDistantLight",
    "feDropShadow",
    "feFlood",
    "feFuncA",
    "feFuncB",
    "feFuncG",
    "feFuncR",
    "feGaussianBlur",
    "feImage",
    "feMerge",
    "feMergeNode",
    "feMorphology",
    "feOffset",
    "fePointLight",
    "feSpecularLighting",
    "feSpotLight",
    "feTile",
    "feTurbulence",
    "foreignObject",
    "glyphRef",
    "linearGradient",
    "radialGradient",
    "textPath",
]
KEPT = ["clipPath", "linearGradient", "radialGradient", "textPath"]
DROPPED = ["animateMotion", "animateTransform", "foreignObject"]
SPELLINGS = [str.lower, str.upper, lambda n: n]


def test_case_table_is_the_spec_table():
    assert _SVG_TAG_NAMES == {name.lower(): name for name in SPEC_TABLE}


def test_kept_and_dropped_names_are_decided():
    assert sorted(n for n in SPEC_TABLE if n.lower() in _ALLOWED_TAGS) == KEPT
    assert sorted(n for n in SPEC_TABLE if n.lower() in _DROP_TAGS) == DROPPED


@pytest.mark.parametrize("name", KEPT)
@pytest.mark.parametrize("spell", SPELLINGS, ids=["lower", "upper", "camel"])
def test_kept_name_is_written_with_its_case(name, spell):
    out = _sanitized_html(
        f"<svg><{spell(name)} id=i><rect></rect></{spell(name)}></svg>"
    )
    assert out == f'<svg><{name} id="i"><rect></rect></{name}></svg>'


def test_gradient_clip_and_text_path_keep_their_attributes():
    src = (
        '<svg viewBox="0 0 8 8">'
        '<linearGradient id="g" gradientUnits="userSpaceOnUse" '
        'gradientTransform="rotate(9)" spreadMethod="pad" x1="0" x2="1">'
        '<stop offset="0" stop-color="red"/></linearGradient>'
        '<radialGradient id="r" cx="1" fx="1" href="#g"></radialGradient>'
        '<clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="1"/></clipPath>'
        '<rect clip-path="url(#c)" fill="url(#g)" width="8"/>'
        '<text><textPath href="#p" startOffset="2">t</textPath></text></svg>'
    )
    assert _sanitized_html(src) == (
        '<svg viewbox="0 0 8 8">'
        '<linearGradient gradienttransform="rotate(9)" gradientunits="userSpaceOnUse" '
        'id="g" spreadmethod="pad" x1="0" x2="1">'
        '<stop offset="0" stop-color="red"></stop></linearGradient>'
        '<radialGradient cx="1" fx="1" href="#g" id="r"></radialGradient>'
        '<clipPath clippathunits="objectBoundingBox" id="c"><rect width="1"></rect></clipPath>'
        '<rect clip-path="url(#c)" fill="url(#g)" width="8"></rect>'
        '<text><textPath href="#p" startoffset="2">t</textPath></text></svg>'
    )


@pytest.mark.parametrize("name", KEPT)
def test_kept_name_gets_the_attribute_policy(name):
    src = (
        f"<svg><{name} onload=hit() onclick=hit() hx-get=/x x-init=hit() "
        f"href=javascript:hit() xlink:href=' jav&#x61;script:hit()' "
        f"style=background:url(javascript:hit()) srcdoc=x formaction=/x "
        f"requiredExtensions=x id=ok>t</{name}></svg>"
    )
    assert _sanitized_html(src) == f'<svg><{name} id="ok">t</{name}></svg>'


@pytest.mark.parametrize("name", DROPPED)
@pytest.mark.parametrize("spell", SPELLINGS, ids=["lower", "upper", "camel"])
def test_dropped_name_goes_with_its_children(name, spell):
    out = _sanitized_html(
        f"<svg><{spell(name)} attributeName=href to=javascript:hit()>"
        f"<img src=x onerror=hit()>t</{spell(name)}><rect></rect></svg>"
    )
    assert out == "<svg><rect></rect></svg>"


@pytest.mark.parametrize("name", sorted(set(SPEC_TABLE) - set(KEPT) - set(DROPPED)))
def test_other_name_is_unwrapped(name):
    out = _sanitized_html(f"<svg><{name} href=x>t<rect></rect></{name}></svg>")
    assert out == "<svg>t<rect></rect></svg>"
