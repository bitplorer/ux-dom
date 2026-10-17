# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

"""Parse an HTML string into ux-dom nodes.

``defHTML(markup)`` (``escape=True``, the default) is the sanitizer for HTML
you do not trust. It is an allow-list: only the formatting tags in
``SAFE_TAGS`` and the attributes in ``SAFE_ATTRIBUTES`` survive. Everything
else is dropped together with its content: scripts, styles, forms, frames,
SVG/MathML, custom elements, event handlers, Alpine (``x-*``, ``@*``, ``:*``),
htmx (``hx-*``), ``data-*`` and ``style``. URL attributes go through
``safe_attr_value``. Comments and declarations are dropped.

``defHTML(markup, escape=False)`` parses markup you wrote yourself and keeps
every tag and attribute, including custom elements, Jinja syntax and
comments. Never pass user input to it.
"""
from __future__ import annotations

import builtins

from ux_dom.dom.src import ext, htmltags, jinjatags, svgtags
from ux_dom.dom.src.parse_html import Comment, Data, Element, tokenize_html
from ux_dom.dom.src.utils import dom_text, raw
from ux_dom.dom.src.utils.dom_util import UNSAFE_URL, safe_attr_value

__all__ = ["defHTML", "SAFE_TAGS", "SAFE_ATTRIBUTES"]

SAFE_TAGS = frozenset(
    {
        "a", "abbr", "b", "bdi", "bdo", "blockquote", "br", "caption", "cite",
        "code", "col", "colgroup", "dd", "del", "details", "dfn", "div", "dl",
        "dt", "em", "figcaption", "figure", "h1", "h2", "h3", "h4", "h5", "h6",
        "hr", "i", "img", "ins", "kbd", "li", "mark", "ol", "p", "pre", "q",
        "rp", "rt", "ruby", "s", "samp", "small", "span", "strong", "sub",
        "summary", "sup", "table", "tbody", "td", "tfoot", "th", "thead",
        "time", "tr", "u", "ul", "var", "wbr",
    }
)
_GLOBAL_ATTRIBUTES = frozenset({"class", "title", "lang", "dir", "role"})
SAFE_ATTRIBUTES: dict[str, frozenset[str]] = {
    "a": frozenset({"href", "rel", "hreflang"}),
    "img": frozenset({"src", "alt", "width", "height", "loading"}),
    "td": frozenset({"colspan", "rowspan", "headers"}),
    "th": frozenset({"colspan", "rowspan", "headers", "scope"}),
    "ol": frozenset({"start", "reversed", "type"}),
    "li": frozenset({"value"}),
    "blockquote": frozenset({"cite"}),
    "q": frozenset({"cite"}),
    "del": frozenset({"cite", "datetime"}),
    "ins": frozenset({"cite", "datetime"}),
    "time": frozenset({"datetime"}),
    "col": frozenset({"span"}),
    "colgroup": frozenset({"span"}),
    "details": frozenset({"open"}),
}
# Text inside these elements is raw by HTML rules; it is never re-escaped.
_RAW_TEXT_TAGS = frozenset({"script", "style"})
# Whitespace inside these elements is content (code indentation).
_PREFORMATTED_TAGS = frozenset({"pre", "textarea"})
_TAG_MODULES = (htmltags, svgtags, jinjatags)

# Dynamic tag classes are cached so parsing never creates a new type per call.
_dynamic_element_registry: dict[str, type[ext.Tags]] = {}


def create_dynamic_element(tag_name: str) -> type[ext.Tags]:
    """Return a cached ``Tags`` subclass for a tag ux-dom does not define."""
    if tag_name not in _dynamic_element_registry:
        cls_name = "".join(part.capitalize() for part in tag_name.split("-")) or "Dynamic"
        if cls_name[0].isdigit():
            cls_name = "Tag" + cls_name
        element = type(cls_name, (ext.Tags,), {"tagname": tag_name, "__module__": __name__})
        _dynamic_element_registry[tag_name] = element
    return _dynamic_element_registry[tag_name]


def _tag_class(name: str) -> type[ext.Tags]:
    candidates = (name + "_", name) if name in builtins.__dict__ else (name, name + "_")
    for module in _TAG_MODULES:
        for candidate in candidates:
            element = getattr(module, candidate, None)
            if isinstance(element, type):
                return element
    return create_dynamic_element(name)


def _safe_attrs(tag: str, attrs: dict) -> dict:
    allowed = SAFE_ATTRIBUTES.get(tag, frozenset())
    out = {}
    for key, value in attrs.items():
        name = str(key).lower()
        if name in _GLOBAL_ATTRIBUTES or name in allowed or name.startswith("aria-"):
            value = "" if value is None else value
            if safe_attr_value(name, value) != UNSAFE_URL:
                out[name] = value
    return out


def _text(data: str) -> str | None:
    """Drop formatting whitespace; keep spaces that separate inline words."""
    if not data.strip():
        return None if "\n" in data else " "
    head = data[: len(data) - len(data.lstrip())]
    tail = data[len(data.rstrip()) :]
    core = data.strip()
    lead = "" if not head or "\n" in head else " "
    trail = "" if not tail or "\n" in tail else " "
    return lead + core + trail


def _build(token: Element, trusted: bool, parent: str = "", pre: bool = False) -> None:
    """Create the node for ``token`` inside the currently open ``with`` frame."""
    if isinstance(token, Data):
        if parent in _RAW_TEXT_TAGS:
            raw(token.data)
            return
        text = token.data.strip("\n") or None if pre else _text(token.data)
        if text is None:
            return
        if trusted and text.strip().startswith("{") and text.strip().endswith("}"):
            raw(text)  # Jinja syntax in author templates
        else:
            dom_text(text)
        return
    if not token.name:  # comment, declaration, processing instruction
        if trusted:
            htmltags.comment(token.data) if isinstance(token, Comment) else raw(token.render())
        return
    name = str(token.name).lower()
    if not trusted and name not in SAFE_TAGS:
        return  # fail closed: drop the element and everything inside it
    attrs = dict(token.attrs or {})
    if not trusted:
        attrs = _safe_attrs(name, attrs)
    pre = pre or name in _PREFORMATTED_TAGS
    with _tag_class(name)(**attrs):
        for child in token.children:
            _build(child, trusted, name, pre)


def defHTML(raw_string, escape: bool = True) -> list[ext.Tags]:  # noqa: N802
    """Parse ``raw_string``; sanitize it unless ``escape=False`` (trusted)."""
    if raw_string is None:
        return []
    nodes: list[ext.Tags] = []
    for token in tokenize_html(str(raw_string), convert_charrefs=True).children:
        with ext.PlaceholderTag() as holder:
            _build(token, trusted=not escape)
        children = list(holder.children)
        holder.clear()
        for child in children:
            child.parent = None
            nodes.append(child if isinstance(child, ext.Tags) else _wrap(child))
    return nodes


def _wrap(node) -> ext.Tags:
    holder = ext.PlaceholderTag()
    holder.add(node)
    return holder
