# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""
Utility classes for creating dynamic html documents
"""

__license__ = """
This file is part of Dominate.

Dominate is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

Dominate is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General
Public License along with Dominate.  If not, see
<http://www.gnu.org/licenses/>.
"""

import html
import re

from jinja2.utils import htmlsafe_json_dumps

from ux_dom.dom.src.dom_tag import dom_tag

__all__ = [
    "escape",
    "escape_attr_minimal",
    "InvalidAttributeName",
    "checked_attr_name",
    "iter_attributes",
    "safe_attr_value",
    "cross_origin",
    "CrossOriginURL",
    "dom_text",
    "raw",
]


_CTRL_ATTR = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def escape(data, quote=True):
    """Escape HTML special chars; strip C0 controls in attribute mode.

    ``quote=True`` escapes both ``"`` and ``'`` (``&#39;``, same as MarkupSafe),
    so output is safe in either attribute quoting style.
    """
    if not isinstance(data, str):
        data = str(data)
    if quote:
        data = _CTRL_ATTR.sub("", data)
    data = data.replace("&", "&" + "amp;")  # Must be done first!
    data = data.replace("<", "&" + "lt;")
    data = data.replace(">", "&" + "gt;")
    if quote:
        data = data.replace('"', "&" + "quot;")
        data = data.replace("'", "&" + "#39;")
    return data


# URL-bearing attributes. A script-capable scheme here is an XSS sink, so the
# renderer fails closed: the value becomes UNSAFE_URL (inert, like Closure's
# "about:invalid#zClosurez"). Applies to every render path, including
# attributes marked unescaped, because no caller needs an executable URL.
URL_ATTRIBUTES = frozenset(
    {
        "href",
        "src",
        "action",
        "formaction",
        "xlink:href",
        "poster",
        "cite",
        "background",
        "data",
        "codebase",
        "longdesc",
        "manifest",
        "ping",
        "icon",
        "archive",
        "usemap",
        "profile",
        "lowsrc",
        "dynsrc",
    }
)
# Attributes whose URL htmx (or its SSE/WebSocket extensions) fetches and
# swaps into the page. A foreign origin there can inject any HTML, so these
# accept relative same-origin URLs only, unless the value is wrapped in
# ``cross_origin(...)``.
SAME_ORIGIN_URL_ATTRIBUTES = frozenset(
    {
        "hx-get",
        "hx-post",
        "hx-put",
        "hx-patch",
        "hx-delete",
        "sse-connect",
        "ws-connect",
    }
)
# Attributes whose value is a whole HTML document, not a URL. A scheme check
# is meaningless there, so they are refused unless the value explicitly opts
# in through the ``__html__`` protocol (MarkupSafe's ``Markup`` and friends).
HTML_ATTRIBUTES = frozenset({"srcdoc"})
UNSAFE_URL = "about:invalid#ux-dom-unsafe-url"
_URL_NOISE = re.compile(r"[\x00-\x20\x7f]+")
# Allow-list, not deny-list: anything not listed here fails closed.
_SAFE_SCHEMES = frozenset({"http", "https", "mailto", "tel"})
_CROSS_ORIGIN_SCHEMES = frozenset({"http", "https", "ws", "wss"})
_SAFE_DATA_URL = re.compile(r"data:image/(?:png|jpeg|jpg|gif|webp)(?:[;,]|$)")


class CrossOriginURL(str):
    """A URL the author allows to point at another origin (see ``cross_origin``)."""


def cross_origin(url):
    """Opt one htmx/SSE/WebSocket URL out of the same-origin rule.

    ``div(hx_get=cross_origin("https://api.example.com/feed"))``. The scheme
    must still be ``http``, ``https``, ``ws`` or ``wss``.
    """
    return CrossOriginURL(url)


class InvalidAttributeName(ValueError):
    """An attribute name that could break out of the tag (fail closed)."""


# HTML attribute names may not contain whitespace, quotes, ">", "/", "=" or
# control characters (WHATWG "attribute name"). Such a name, e.g. from a
# ``**user_dict`` spread, could inject a new attribute such as onmouseover.
_BAD_ATTR_NAME = re.compile(r"[\s\"'>/=\x00-\x1f\x7f]")


def checked_attr_name(name):
    """Return ``name`` as text, or raise InvalidAttributeName."""
    text = str(name)
    if not text or _BAD_ATTR_NAME.search(text):
        raise InvalidAttributeName(f"invalid attribute name: {text!r}")
    return text


def escape_attr_minimal(data):
    """Escape only ``&`` and ``"``: the least that keeps a value inside ``"..."``.

    Used for attributes that opt out of full escaping (Alpine JSON and
    handlers keep ``'``, ``<`` and ``>`` readable). The browser decodes the
    entities back, so the value is unchanged; it just cannot close the quote.
    """
    return str(data).replace("&", "&amp;").replace('"', "&quot;")


def iter_attributes(attributes, *, unescaped=frozenset(), skip=frozenset()):
    """Yield `` name="value"`` fragments: the one attribute serializer.

    Every renderer uses this, so name validation, the URL allow-list and
    escaping cannot drift apart. ``False`` omits an attribute, ``None``
    renders it bare, dict/list values render as single-quoted JSON, and names
    in ``unescaped`` keep ``'``, ``<`` and ``>`` readable (``&`` and ``"``
    are still escaped).
    """
    for name, value in sorted(attributes.items()):
        if name in skip or value is False:
            continue
        name = checked_attr_name(name)
        if value is None:
            yield f" {name}"
        elif isinstance(value, (dict, list)):
            yield " %s='%s'" % (name, escape(htmlsafe_json_dumps(value), quote=False))
        else:
            if name == "class":
                value = " ".join(str(value).split())
            value = safe_attr_value(name, value)
            text = escape_attr_minimal(value) if name in unescaped else escape(value)
            yield f' {name}="{text}"'


def _is_safe_url(text):
    """True for relative URLs, allow-listed schemes, and raster data: images."""
    # Browsers decode entities before parsing the URL; check what they see.
    probe = _probe(text)
    head = re.split(r"[/?#]", probe, maxsplit=1)[0]
    if ":" not in head:
        return True  # relative: "/a", "a/b", "?q", "#f", "//host/x"
    scheme = head.split(":", 1)[0]
    if scheme == "data":
        return _SAFE_DATA_URL.match(probe) is not None
    return scheme in _SAFE_SCHEMES


def _probe(text):
    return _URL_NOISE.sub("", html.unescape(text)).lower()


def _is_same_origin_url(text):
    """True for relative URLs that stay on this origin (no scheme, no ``//host``)."""
    probe = _probe(text)
    if probe.startswith(("//", "\\\\", "/\\", "\\/")):
        return False
    return ":" not in re.split(r"[/?#]", probe, maxsplit=1)[0]


def _is_safe_cross_origin_url(text):
    head = re.split(r"[/?#]", _probe(text), maxsplit=1)[0]
    return ":" not in head or head.split(":", 1)[0] in _CROSS_ORIGIN_SCHEMES


def safe_attr_value(attribute, value):
    """Return ``value``, or UNSAFE_URL if it is not safe for ``attribute``.

    URL attributes keep only relative URLs, ``http``, ``https``, ``mailto``,
    ``tel`` and ``data:image/{png,jpeg,gif,webp}`` (never SVG). The check runs
    on ``str(value)`` after HTML entities are decoded and the C0 controls and
    spaces that browsers ignore inside a scheme are removed.

    HTML attributes (``srcdoc``) are refused unless the value implements
    ``__html__``; then that HTML is returned (it is still attribute-escaped).

    For checked attributes the return value is always the ``str`` that was
    checked, so the renderer never stringifies the original object again.
    """
    name = str(attribute).lower()
    if name in HTML_ATTRIBUTES:
        html_method = getattr(value, "__html__", None)
        return str(html_method()) if callable(html_method) else UNSAFE_URL
    if name in SAME_ORIGIN_URL_ATTRIBUTES:
        text = str(value)
        if isinstance(value, CrossOriginURL):
            return text if _is_safe_cross_origin_url(text) else UNSAFE_URL
        return text if _is_same_origin_url(text) else UNSAFE_URL
    if name not in URL_ATTRIBUTES:
        return value
    # Stringify once and return that text: re-stringifying ``value`` later
    # could yield something other than what was checked.
    text = str(value)
    return text if _is_safe_url(text) else UNSAFE_URL


_escape_text = escape  # dom_text's ``escape`` parameter shadows the function


class dom_text(dom_tag):
    """
    Just a string. useful for inside context managers
    """

    is_pretty = False
    is_inline = False

    def __init__(self, _text, escape=True):
        if escape:
            self.text = _escape_text(_text)
        else:
            self.text = _text
        super().__init__()

    def _render(self, sb, *a, **kw):
        sb.append(self.text)
        return sb


def raw(s):
    """
    Inserts a raw string into the DOM. Unsafe.
    """
    return dom_text(s, escape=False)
