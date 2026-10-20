# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""Parse HTML strings into ux-dom nodes (defHTML) and related helpers.

One allowlist sanitizer. Safe tags and their attributes are kept; everything
else is stripped. String HTML is always sanitized: ``escape`` is accepted for
compatibility and never bypasses the allowlist. Text is escaped on both
``escape`` settings so a ``<`` in text cannot reopen a tag. Character
references are re-emitted here (``&amp;``, ``&#39;``) and are not passed
through ``escape()``. Trusted markup uses ``raw()`` / ``Markup``.

Elements a browser parses as raw text (``noscript``, ``xmp``, ``template``
content, …) and comments are dropped: the Python parser reads them as markup,
so they are where the two parsers disagree (mutation XSS).

Fragment mode is the default. Document mode (doctype, ``html``/``head``/
``body``, safe ``meta``, stylesheet/icon ``link``, ``style``) is a keyword
the caller passes (``document=True``); the input never selects it.
Unknown elements are unwrapped; custom elements are kept only when named in
``allow_custom_elements``. Policy: docs/adr/0002-html-string-sanitizer-policy.md.
"""

import builtins
import html
import re
from collections.abc import Iterable
import types
import typing as T
from dataclasses import dataclass, field
from html.entities import name2codepoint

from ux_dom.dom.src import ext, htmltags, jinjatags, svgtags
from ux_dom.dom.src.htmltags import html_tag
from ux_dom.dom.src.parse_html import (
    Char,
    Comment,
    Declaration,
    Element,
    Entity,
    tokenize_html,
)
from ux_dom.dom.src.utils import dom_text, escape

__all__ = ["StringToHTML", "defHTML"]


# Cache dynamic tag classes so defHTML does not pollute ``__main__`` or
# re-create a new type for the same custom tag name on every parse.
_dynamic_element_registry: dict[str, T.Type[ext.Tags]] = {}


def create_dynamic_element(tag_name: str) -> T.Type[ext.Tags]:
    """Build (or reuse) a Tags subclass for unknown HTML/custom tag names.

    Previously this set attributes on ``sys.modules['__main__']`` and required
    ``__main__.__file__``, which polluted interactive sessions and crashed under
    some embedders. Classes are cached on a private registry instead.
    """
    if tag_name in _dynamic_element_registry:
        return _dynamic_element_registry[tag_name]

    cls_name = "".join(map(lambda x: x.capitalize(), tag_name.split("-"))) or "Dynamic"
    # Ensure a valid identifier
    if cls_name[0].isdigit():
        cls_name = "Tag" + cls_name

    class _Element(ext.Tags):
        tagname = tag_name

    _Element.__qualname__ = cls_name
    _Element.__name__ = cls_name
    _Element.__module__ = "ux_dom.dom.src.html_string"
    element: T.Type[ext.Tags] = _Element
    _dynamic_element_registry[tag_name] = element
    return element


# Tags dropped with their children. Unknown tags are unwrapped instead, so
# their text stays and the tag does not. ``link`` / ``meta`` / ``style`` are
# not in this set: a fragment drops them, a document keeps them under rules.
#
# The raw-text group is parsed as markup by Python but as text by a browser
# (``noscript`` with scripting on, ``xmp``, ``noembed``, ``noframes``,
# ``iframe``, ``plaintext``) or lives in an inert template document. Keeping
# any of them lets a ``</noscript>`` inside a comment or attribute end the
# element early in the browser and turn the rest into live markup.
_DROP_TAGS = frozenset(
    {
        "script",
        "noscript",
        "noembed",
        "noframes",
        "xmp",
        "plaintext",
        "template",
        "iframe",
        "object",
        "embed",
        "base",
        "frame",
        "frameset",
        "applet",
        "animate",
        "animatetransform",
        "animatemotion",
        "set",
        "foreignobject",
        "math",
        "maction",
    }
)
_DOCUMENT_ONLY_TAGS = frozenset({"link", "meta", "style"})

# Known-safe tags for a fragment. Document mode adds ``_DOCUMENT_ONLY_TAGS``.
_ALLOWED_TAGS = frozenset(
    {
        "a",
        "abbr",
        "address",
        "area",
        "article",
        "aside",
        "audio",
        "b",
        "bdi",
        "bdo",
        "blockquote",
        "body",
        "br",
        "button",
        "canvas",
        "caption",
        "cite",
        "code",
        "col",
        "colgroup",
        "data",
        "datalist",
        "dd",
        "del",
        "details",
        "dfn",
        "dialog",
        "div",
        "dl",
        "dt",
        "em",
        "fieldset",
        "figcaption",
        "figure",
        "font",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "head",
        "header",
        "hgroup",
        "hr",
        "html",
        "i",
        "img",
        "input",
        "ins",
        "kbd",
        "label",
        "legend",
        "li",
        "main",
        "map",
        "mark",
        "menu",
        "meter",
        "nav",
        "ol",
        "optgroup",
        "option",
        "output",
        "p",
        "picture",
        "pre",
        "progress",
        "q",
        "rp",
        "rt",
        "ruby",
        "s",
        "samp",
        "section",
        "select",
        "slot",
        "small",
        "source",
        "span",
        "strong",
        "sub",
        "summary",
        "sup",
        "table",
        "tbody",
        "td",
        "textarea",
        "tfoot",
        "th",
        "thead",
        "time",
        "title",
        "tr",
        "track",
        "u",
        "ul",
        "var",
        "video",
        "wbr",
        # SVG geometry. Animation / foreignObject / math stay in ``_DROP_TAGS``.
        "circle",
        "defs",
        "desc",
        "ellipse",
        "g",
        "line",
        "marker",
        "mask",
        "path",
        "pattern",
        "polygon",
        "polyline",
        "rect",
        "stop",
        "svg",
        "switch",
        "symbol",
        "text",
        "tspan",
        "use",
        "view",
    }
)

_GLOBAL_ATTRS = frozenset(
    {
        "accesskey",
        "autocapitalize",
        "autofocus",
        "class",
        "contenteditable",
        "dir",
        "draggable",
        "enterkeyhint",
        "hidden",
        "id",
        "inert",
        "inputmode",
        "lang",
        "popover",
        "role",
        "slot",
        "spellcheck",
        "style",
        "tabindex",
        "title",
        "translate",
    }
)

_TAG_ATTRS: dict[str, frozenset[str]] = {
    "a": frozenset(
        {"href", "target", "rel", "hreflang", "type", "download", "referrerpolicy"}
    ),
    "area": frozenset({"alt", "coords", "shape", "href", "target", "rel", "download"}),
    "audio": frozenset({"src", "controls", "loop", "muted", "preload", "autoplay"}),
    "blockquote": frozenset({"cite"}),
    "button": frozenset(
        {
            "type",
            "name",
            "value",
            "disabled",
            "form",
            "formaction",
            "formenctype",
            "formmethod",
            "formnovalidate",
            "formtarget",
        }
    ),
    "col": frozenset({"span"}),
    "colgroup": frozenset({"span"}),
    "data": frozenset({"value"}),
    "del": frozenset({"cite", "datetime"}),
    "details": frozenset({"open"}),
    "font": frozenset({"color", "face", "size"}),
    "form": frozenset(
        {"action", "method", "enctype", "name", "novalidate", "target", "autocomplete"}
    ),
    "html": frozenset({"xmlns"}),
    "img": frozenset(
        {
            "src",
            "alt",
            "width",
            "height",
            "srcset",
            "sizes",
            "loading",
            "decoding",
            "referrerpolicy",
            "crossorigin",
            "usemap",
            "ismap",
        }
    ),
    "input": frozenset(
        {
            "type",
            "name",
            "value",
            "placeholder",
            "checked",
            "disabled",
            "readonly",
            "required",
            "min",
            "max",
            "step",
            "maxlength",
            "minlength",
            "pattern",
            "size",
            "multiple",
            "accept",
            "alt",
            "src",
            "list",
            "form",
            "autocomplete",
            "width",
            "height",
            "formaction",
            "formenctype",
            "formmethod",
            "formnovalidate",
            "formtarget",
        }
    ),
    "ins": frozenset({"cite", "datetime"}),
    "label": frozenset({"for", "form"}),
    "li": frozenset({"value"}),
    "link": frozenset(
        {
            "href",
            "rel",
            "type",
            "media",
            "sizes",
            "as",
            "crossorigin",
            "hreflang",
            "referrerpolicy",
        }
    ),
    "meta": frozenset(
        {"charset", "content", "name", "property", "http-equiv", "media"}
    ),
    "meter": frozenset({"value", "min", "max", "low", "high", "optimum"}),
    "ol": frozenset({"start", "reversed", "type"}),
    "optgroup": frozenset({"label", "disabled"}),
    "option": frozenset({"value", "selected", "disabled", "label"}),
    "progress": frozenset({"value", "max"}),
    "q": frozenset({"cite"}),
    "select": frozenset(
        {"name", "multiple", "disabled", "required", "size", "form", "autocomplete"}
    ),
    "source": frozenset({"src", "type", "srcset", "sizes", "media"}),
    "style": frozenset({"media", "type", "nonce"}),
    "td": frozenset({"colspan", "rowspan", "headers", "abbr"}),
    "textarea": frozenset(
        {
            "name",
            "rows",
            "cols",
            "placeholder",
            "disabled",
            "readonly",
            "required",
            "maxlength",
            "minlength",
            "wrap",
            "autocomplete",
            "form",
        }
    ),
    "th": frozenset({"colspan", "rowspan", "headers", "scope", "abbr"}),
    "time": frozenset({"datetime"}),
    "track": frozenset({"src", "kind", "srclang", "label", "default"}),
    "video": frozenset(
        {
            "src",
            "controls",
            "poster",
            "preload",
            "loop",
            "muted",
            "autoplay",
            "width",
            "height",
            "crossorigin",
        }
    ),
}

_SVG_TAGS = frozenset(
    {
        "circle",
        "defs",
        "desc",
        "ellipse",
        "g",
        "line",
        "marker",
        "mask",
        "path",
        "pattern",
        "polygon",
        "polyline",
        "rect",
        "stop",
        "svg",
        "switch",
        "symbol",
        "text",
        "tspan",
        "use",
        "view",
    }
)
_SVG_ATTRS = frozenset(
    {
        "cx",
        "cy",
        "d",
        "fill",
        "fill-opacity",
        "font-family",
        "font-size",
        "fx",
        "fy",
        "height",
        "href",
        "offset",
        "opacity",
        "pathlength",
        "points",
        "preserveaspectratio",
        "r",
        "rx",
        "ry",
        "stop-color",
        "stop-opacity",
        "stroke",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-opacity",
        "stroke-width",
        "text-anchor",
        "transform",
        "viewbox",
        "width",
        "x",
        "x1",
        "x2",
        "xlink:href",
        "xmlns",
        "y",
        "y1",
        "y2",
    }
)

# URL attributes that remain on the allowlist. ``hx-*`` is not here: those
# attributes are never kept. Scheme checks match the renderer; document
# ``<link href>`` is stricter (same-origin or https) in ``_link_href_ok``.
_URL_ATTRS = frozenset(
    {
        "href",
        "src",
        "xlink:href",
        "formaction",
        "action",
        "poster",
        "cite",
        "background",
    }
)


def _norm_attr_name(key: str) -> str:
    """Match renderer: leading ``_`` is stripped (``_onclick`` → ``onclick``)."""
    k = str(key)
    while k.startswith("_"):
        k = k[1:]
    return k.lower()


def _scheme_is_dangerous(value: str) -> bool:
    # Strip C0/whitespace that browsers ignore before the scheme.
    cleaned = "".join(ch for ch in value if ch.isprintable() and not ch.isspace())
    low = cleaned.lower()
    for bad in ("javascript:", "vbscript:", "data:text/html"):
        if low.startswith(bad):
            return True
    return False


def _style_is_dangerous(value: str) -> bool:
    low = value.lower().replace("\\", "").replace("\0", "")
    return "javascript:" in low or "expression(" in low or "vbscript:" in low


def _link_href_ok(value: str) -> bool:
    """Document ``<link href>``: relative same-origin, or ``https``.

    ``http://`` (cross-origin; no document origin is known here),
    protocol-relative ``//host``, and ``javascript:`` fail. This is the
    document-mode rule. Other URL attributes keep the renderer scheme check.
    """
    cleaned = "".join(
        ch for ch in html.unescape(value) if ch.isprintable() and not ch.isspace()
    )
    low = cleaned.lower()
    if not low or low.startswith(("//", "\\\\", "/\\", "\\/")):
        return False
    head = re.split(r"[/?#]", low, maxsplit=1)[0]
    if ":" not in head:
        return True
    return head.split(":", 1)[0] == "https"


# https://html.spec.whatwg.org/#valid-custom-element-name (ASCII subset).
_CUSTOM_ELEMENT_NAME = re.compile(r"[a-z][a-z0-9._-]*-[a-z0-9._-]*")
_RESERVED_CUSTOM_NAMES = frozenset(
    {
        "annotation-xml",
        "color-profile",
        "font-face",
        "font-face-src",
        "font-face-uri",
        "font-face-format",
        "font-face-name",
        "missing-glyph",
    }
)


def _custom_element_rules(
    names: T.Optional[Iterable[str]],
) -> frozenset[str]:
    """Validate ``allow_custom_elements``: exact names or a ``prefix-*``.

    Only valid custom element names (lowercase, with a hyphen, not reserved)
    are accepted, so the opt-in cannot re-allow ``script`` or any other
    built-in tag.
    """
    if names is None:
        return frozenset()
    if isinstance(names, str):
        names = [names]
    rules = set()
    for name in names:
        text = str(name)
        stem = text[:-1] if text.endswith("*") else text
        if (
            not _CUSTOM_ELEMENT_NAME.fullmatch(stem)
            or stem in _RESERVED_CUSTOM_NAMES
            or "*" in stem
        ):
            raise ValueError(
                f"allow_custom_elements: {text!r} is not a custom element "
                "name (lowercase, contains '-') or a 'prefix-*' pattern"
            )
        rules.add(text)
    return frozenset(rules)


def _custom_allowed(name: str, rules: frozenset[str]) -> bool:
    if not rules or name in _RESERVED_CUSTOM_NAMES:
        return False
    if not _CUSTOM_ELEMENT_NAME.fullmatch(name):
        return False
    return any(
        name == rule or (rule.endswith("*") and name.startswith(rule[:-1]))
        for rule in rules
    )


def _tag_allowed(name: str, document: bool, custom: frozenset[str]) -> bool:
    if name in _ALLOWED_TAGS:
        return True
    if document and name in _DOCUMENT_ONLY_TAGS:
        return True
    return _custom_allowed(name, custom)


def _style_text(token) -> T.Optional[str]:
    """Document ``<style>`` text, verbatim, or ``None`` to drop the element.

    CSS is raw text: escaping it breaks ``a > b``. Any ``<`` is refused, which
    covers ``</style`` in every case and markup that a browser would parse in
    foreign content (``<svg><style>`` children are elements there).
    """
    parts = []
    for child in token.children:
        if getattr(child, "name", "") or not isinstance(
            getattr(child, "data", None), str
        ):
            return None
        parts.append(child.data)
    css = "".join(parts)
    return None if "<" in css else css


def _reference_text(token: Char | Entity) -> str:
    """Re-emit a character reference without calling ``escape()``.

    ``escape()`` on main encodes the leading ``&``, so a reference must not
    be passed through it. Unknown names stay the letters the parser already
    produced (``AT&T`` → ``ATT``).
    """
    if isinstance(token, Char):
        return token.render()
    name = str(token.data)
    if name in name2codepoint:
        return f"&{name};"
    return name


def _attr_kept(tag: str, key: str, value) -> bool:
    kl = _norm_attr_name(key)
    if not kl or kl == "srcdoc":
        return False
    if kl.startswith("on") or kl.startswith("hx-") or kl.startswith("data-hx-"):
        return False
    if (
        kl.startswith("x-")
        or kl.startswith("x_")
        or kl.startswith("@")
        or kl.startswith(":")
    ):
        return False
    allowed = (
        kl in _GLOBAL_ATTRS
        or kl in _TAG_ATTRS.get(tag, frozenset())
        or (tag in _SVG_TAGS and kl in _SVG_ATTRS)
        or kl.startswith("aria-")
        or (kl.startswith("data-") and not kl.startswith("data-hx-"))
    )
    if not allowed:
        return False
    if not isinstance(value, str):
        return True
    if kl == "style" and _style_is_dangerous(value):
        return False
    if kl in _URL_ATTRS and _scheme_is_dangerous(value):
        return False
    if kl == "srcset" and any(
        _scheme_is_dangerous(candidate.strip())
        for candidate in value.split(",")
    ):
        return False
    return True


def _filter_attrs(tag: str, attrs: dict) -> dict:
    if not attrs:
        return {}
    return {
        key: value
        for key, value in dict(attrs).items()
        if _attr_kept(tag, key, value)
    }


# ``http-equiv`` values that only describe the document. ``refresh``,
# ``set-cookie``, ``content-security-policy``, ``default-style`` and the rest
# change behaviour, so a meta that carries one is dropped.
_META_HTTP_EQUIV = frozenset({"content-type", "content-language", "x-ua-compatible"})


def _meta_attrs(attrs: dict) -> dict | None:
    for key, value in dict(attrs or {}).items():
        if (
            _norm_attr_name(key) == "http-equiv"
            and str(value).strip().lower() not in _META_HTTP_EQUIV
        ):
            return None
    return _filter_attrs("meta", attrs)


def _link_attrs(attrs: dict) -> dict | None:
    rel = ""
    href = None
    for key, value in dict(attrs or {}).items():
        name = _norm_attr_name(key)
        if name == "rel":
            rel = str(value).strip().lower()
        elif name == "href":
            href = value
    tokens = rel.split()
    if not tokens or any(token not in {"stylesheet", "icon"} for token in tokens):
        return None
    if href is None or not _link_href_ok(str(href)):
        return None
    return _filter_attrs("link", attrs)


def _text_data(raw: str) -> str:
    """Keep same-line spaces. Newlines are source indentation and drop."""
    if "\n" in raw:
        return raw.strip("\n").strip(" ").strip("\n")
    if raw.strip(" "):
        return raw
    return ""


@dataclass
class StringToHTML(object):
    # AST round-trip (HTML ↔ Python code object) is not implemented.
    # from https://stackoverflow.com/questions/68577587/how-to-find-the-ast-assignment-node-related-to-the-instance-creation
    # this.ast_object can be easily used to create python code for any html object
    # https://stackoverflow.com/a/68584740 for parsing a python object into an ast_object
    # https://stackoverflow.com/a/63212256 for unparsing a python ast_object

    html_string_or_token: T.Union[str, Element, list[Element], ext.Tags]
    modules: list[types.ModuleType] = field(default_factory=list)
    # Accepted for compatibility. String HTML is always sanitized.
    escape: bool = field(default=True)
    # Chosen by the caller, never inferred from the input.
    document: bool = field(default=False)
    allow_custom_elements: T.Optional[Iterable[str]] = field(default=None)

    def __post_init__(self):
        self._custom = _custom_element_rules(self.allow_custom_elements)
        self.allow_custom_elements = self._custom
        if isinstance(self.html_string_or_token, (str, html_tag)):
            raw = (
                self.html_string_or_token
                if isinstance(self.html_string_or_token, str)
                else str(self.html_string_or_token)
            )
            self.tokens = tokenize_html(raw).children
        else:
            self.tokens = self.html_string_or_token

        # for html, svg and jinja tags lookup
        if htmltags not in self.modules:
            self.modules.append(htmltags)

        if svgtags not in self.modules:
            self.modules.append(svgtags)

        if jinjatags not in self.modules:
            self.modules.append(jinjatags)

    def _child_parser(self, tokens) -> "StringToHTML":
        return StringToHTML(
            tokens,
            modules=self.modules,
            escape=self.escape,
            document=self.document,
            allow_custom_elements=self._custom,
        )

    def _add_text(self, tag, text: str, *, already_escaped: bool):
        with tag or ext.PlaceholderTag() as tag:  # type: ignore[assignment]
            # ``already_escaped`` text must not go through ``escape()`` again.
            # Character references are in that bucket. Raw data is escaped
            # first, on both escape settings, so ``<`` cannot reopen a tag.
            dom_text(text, escape=False if already_escaped else True)
        return tag

    def _unwrap(self, token, tag):
        children = list(token.children)
        if not children:
            return tag
        if tag is not None:
            for child in children:
                self._child_parser([child]).parse(tag=tag)
            return tag
        holder = ext.PlaceholderTag()
        for child in children:
            self._child_parser([child]).parse(tag=holder)
        return holder if holder.children else tag

    def parse(self, tag: T.Optional[ext.Tags] = None) -> T.Union[str, ext.Tags, None]:
        for token in self.tokens:  # type: ignore[union-attr]
            if isinstance(token, (Char, Entity)):
                text = _reference_text(token)
                if text:
                    tag = self._add_text(tag, text, already_escaped=True)
                continue

            if isinstance(token, Declaration) and str(token.data).lower().startswith(
                "doctype"
            ):
                if not self.document:
                    # A fragment has no doctype; do not leak it as text.
                    continue
                rest = str(token.data).split(None, 1)
                label = rest[1] if len(rest) > 1 else "html"
                if tag is not None:
                    with tag:
                        htmltags.DocType(label)
                else:
                    tag = htmltags.DocType(label)
                continue

            if not token.name:
                # Comments are dropped: ``--!>`` and friends end a comment
                # differently in Python and in a browser.
                if isinstance(token, Comment):
                    continue
                # Data. Newlines are source indentation. A space on the same
                # line as the words belongs to the text.
                if hasattr(token, "data"):
                    data = _text_data(token.data)
                    if not data:
                        continue
                    with tag or ext.PlaceholderTag() as tag:  # type: ignore[assignment]
                        # Braced text is text. Jinja stays the tag DSL or
                        # raw(), not a hole in this parser.
                        dom_text(escape(data), escape=False)
                continue

            name = str(token.name).lower()
            if name in _DROP_TAGS or (name in _DOCUMENT_ONLY_TAGS and not self.document):
                continue
            if not _tag_allowed(name, self.document, self._custom):
                tag = self._unwrap(token, tag)
                continue

            css = None
            kept: T.Optional[dict]
            if name == "style":
                css = _style_text(token)
                kept = None if css is None else _filter_attrs(name, dict(token.attrs or {}))
            elif name == "meta":
                kept = _meta_attrs(dict(token.attrs or {}))
            elif name == "link":
                kept = _link_attrs(dict(token.attrs or {}))
            else:
                kept = _filter_attrs(name, dict(token.attrs or {}))
            if kept is None:
                continue
            attrs = kept

            element = None
            tag_name = token.name
            if tag_name in builtins.__dict__:
                # work around for builtins like 'input' tag
                tag_name = "".join([token.name, "_"])

            for module in self.modules:
                try:
                    element = getattr(module, tag_name)
                    if element is not None:
                        break
                except (AttributeError,):
                    pass
            if element is None:
                element = create_dynamic_element(tag_name=tag_name)

            if tag is not None:
                with tag:
                    with element(**attrs) as child_tag:
                        self._fill(child_tag, token, css)
            else:
                with element(**attrs) as tag:
                    self._fill(tag, token, css)
        return tag

    def _fill(self, element, token, css: T.Optional[str]) -> None:
        if css is not None:
            # Raw text, checked by ``_style_text``: verbatim, never escaped.
            if css:
                dom_text(css, escape=False)
            return
        self._child_parser(token.children).parse(tag=element)

    def __repr__(self):
        return str(self.parse())


# don't decorate defHTML with functools.lru_cache because if defHTML is used in isolation
# like:
# with div() as parent_div:
#   child_element = defHTML("some html string")
#
# with lru_cache decorated on defHTML the evaluation of child_element at run time will not happen twice
# and thus parent_div will never add child_element in subsequest runs thus better way to cache defHTML
# evaluation is to cache the method where it is used.
def defHTML(
    raw_string,
    escape=True,
    *,
    document: bool = False,
    allow_custom_elements: T.Optional[Iterable[str]] = None,
) -> T.List[ext.Tags]:  # noqa
    """Parse an HTML string into sanitized ux-dom nodes.

    String HTML is always sanitized. ``escape`` is accepted for compatibility
    and does not bypass the allowlist; trusted markup uses ``raw()`` /
    ``Markup``. ``document=True`` (caller's choice, never inferred) keeps the
    doctype and safe ``meta`` / ``link`` / ``style``. ``allow_custom_elements``
    names custom elements (``"x-counter"``) or a ``"prefix-*"`` pattern to
    keep instead of unwrapping.
    """
    if raw_string is None:
        return []
    if not isinstance(raw_string, str):
        raw_string = str(raw_string)
    custom = _custom_element_rules(allow_custom_elements)
    tokens = tokenize_html(raw_string).children
    elements = []
    for token in tokens:
        element = StringToHTML(
            [token],
            escape=escape,
            document=document,
            allow_custom_elements=custom,
        ).parse()
        if element:
            assert isinstance(
                element, ext.Tags
            ), f"{element=} is not instance of {ext.Tags}"
            elements.append(element)
    return elements


def _sanitized_html(
    raw_string,
    escape=True,
    *,
    document: bool = False,
    allow_custom_elements: T.Optional[Iterable[str]] = None,
) -> str:
    """String form of ``defHTML``. Not a second sanitizer and not public."""
    return "".join(
        element.__render__(pretty=False)
        for element in defHTML(
            raw_string,
            escape=escape,
            document=document,
            allow_custom_elements=allow_custom_elements,
        )
    )


# if __name__ == '__main__':
# from ux_dom.dom import ConcatTag, For, Var, div, li, raw, script, ul

# print(defHTML("<li><ul><i><!--Hello World--></i></ul><a href='www.google.com'></a></li>"))
#     class XName(ext.Tags):
#         tagname = "x-name"


# print(defHTML(div("hello", div("Jai SHree Ram"), script(raw("function () => {}")), className="sdaf")).parse())
# print(div("hello", div("Jai SHree Ram"), script(raw("function () => {}")), className="sdaf"))
# print(defHTML(str(div("hello", div("Jai SHree Ram"), script(raw("function () => {}")), className="sdaf", x_data=None))))
# x = HTMLToPy(str(XName("hello", Var("haha"), ul(For("name in names", li(Var("name")))),
#                        div("Jai SHree Ram aa", className="safn"), script(raw("function () => {}")),
#                         script(src="https://unpkg.com/filepond/dist/filepond.js"),
#                         className="sdaf", x_data={}, x_transition_enter="")))
# print(x)
# print(XName("hello >", Var("haha >"), ul(For("name in names", li(Var("name")))),
#             div("Jai SHree Ram   a ", className="safn"), script(raw("function () => {}")),
#                         script(src="https://unpkg.com/filepond/dist/filepond.js"),
#                         className="sdaf", x_data={}, x_transition_enter=""))
# print(defHTML(str(ul(For("name in names", li(Var("name")))))))
