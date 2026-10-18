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

from ux_dom.dom.src.dom_tag import dom_tag

try:
    basestring = basestring
except NameError:
    basestring = str
    unichr = chr

__all__ = [
    "include",
    "system",
    "escape",
    "escape_attr_minimal",
    "InvalidAttributeName",
    "checked_attr_name",
    "unescape",
    "url_escape",
    "url_unescape",
    "lazy",
    "dom_text",
    "raw",
    "neutralize_raw_text",
    "safe_attr_value",
    "UNSAFE_URL",
    "URL_ATTRIBUTES",
    "SAME_ORIGIN_URL_ATTRIBUTES",
    "cross_origin",
    "CrossOriginURL",
]


def include(f):
    """
    includes the contents of a file on disk.
    takes a filename
    """
    fl = open(f, "r")
    data = fl.read()
    fl.close()
    return raw(data)


def system(cmd, data=None):
    """
    pipes the output of a program
    """
    import subprocess

    s = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    out, err = s.communicate(data)
    return out.decode("utf8")


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


# Raw text elements (HTML spec §13.1.2): their text is never entity-decoded by
# the browser, so HTML-escaping corrupts JS/CSS. The only hazards are sequences
# that end the element early or (script only) enter the escaped states.
_RAW_TEXT_HAZARDS = {
    "script": re.compile(r"</(script)|<!--", re.IGNORECASE),
    "style": re.compile(r"</(style)", re.IGNORECASE),
}


def neutralize_raw_text(data, tagname):
    """Make text safe as the content of a raw text element without escaping it.

    ``</script`` / ``</style`` (any case) become ``<\\/script`` / ``<\\/style`` —
    identical meaning inside JS and CSS strings, but no longer an end tag.
    In ``<script>``, ``<!--`` becomes ``<\\!--`` so the parser never enters the
    script-data-escaped states (spec "restrictions for contents of script
    elements"). Everything else (``<``, ``&``, quotes) is emitted verbatim.
    """
    if not isinstance(data, str):
        data = str(data)
    pattern = _RAW_TEXT_HAZARDS.get(str(tagname).lower())
    if pattern is None:
        return data

    def _sub(m):
        if m.group(1) is not None:
            return "<\\/" + m.group(1)
        return "<\\!--"

    return pattern.sub(_sub, data)


# URL-bearing attributes. A script-capable scheme here is an XSS sink, so the
# renderer fails closed: the value becomes UNSAFE_URL (inert, like Closure's
# "about:invalid#zClosurez"). Applies to every render path, including
# attributes marked unescaped, because no caller needs an executable URL.
URL_ATTRIBUTES = frozenset(
    {
        "href", "src", "action", "formaction", "xlink:href", "poster",
        "cite", "background", "data", "codebase", "longdesc",
        "manifest", "ping", "icon", "archive", "usemap", "profile",
        "lowsrc", "dynsrc",
    }
)
# htmx / SSE / WS fetch+swap sinks: relative same-origin only unless
# wrapped in ``cross_origin(...)``. Includes data-* aliases.
SAME_ORIGIN_URL_ATTRIBUTES = frozenset(
    {
        "hx-get", "hx-post", "hx-put", "hx-patch", "hx-delete",
        "data-hx-get", "data-hx-post", "data-hx-put", "data-hx-patch", "data-hx-delete",
        "sse-connect", "ws-connect",
        "data-sse-connect", "data-ws-connect",
        "hx-sse", "hx-ws",
        # htmx 1.9.2 getAttributeValue reads data-<name> as well as the bare name.
        "data-hx-sse", "data-hx-ws",
    }
)
_SSE_WS_ATTRIBUTES = frozenset({"hx-sse", "hx-ws", "data-hx-sse", "data-hx-ws"})
# ECMAScript \s: WhiteSpace plus LineTerminator. Python str.split() omits U+FEFF.
_JS_WS = re.compile(
    "[\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+"
)
# Lowercased, because the probe already folded case. Empty is refused by
# ``not name`` below; this set is the rest of ``[A-Za-z0-9_.-]+``.
_SSE_WS_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_.-")
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


def _probe(text):
    return _URL_NOISE.sub("", html.unescape(text)).lower()


def _is_protocol_relative(probe):
    return probe.startswith(("//", "\\\\", "/\\", "\\/"))


def _is_safe_url(text):
    """True for relative same-host URLs, allow-listed schemes, raster data: images.

    Protocol-relative ``//host/...`` is refused (it is cross-origin).
    """
    probe = _probe(text)
    if _is_protocol_relative(probe):
        return False
    head = re.split(r"[/?#]", probe, maxsplit=1)[0]
    if ":" not in head:
        return True  # relative: "/a", "a/b", "?q", "#f"
    scheme = head.split(":", 1)[0]
    if scheme == "data":
        return _SAFE_DATA_URL.match(probe) is not None
    return scheme in _SAFE_SCHEMES


def _relative_same_origin_probe(probe):
    """``probe`` is already noise-stripped. Relative only: no scheme, no ``//``."""
    if not probe or _is_protocol_relative(probe):
        return False
    return ":" not in re.split(r"[/?#]", probe, maxsplit=1)[0]


def _cross_origin_probe(probe):
    """``probe`` is already noise-stripped. http/https/ws/wss, or a relative URL."""
    if _is_protocol_relative(probe):
        return False
    if not probe:
        return True
    head = re.split(r"[/?#]", probe, maxsplit=1)[0]
    return ":" not in head or head.split(":", 1)[0] in _CROSS_ORIGIN_SCHEMES


def _is_same_origin_url(text):
    """True for relative URLs that stay on this origin (no scheme, no ``//host``)."""
    probe = _probe(text)
    if not probe:
        return True
    return _relative_same_origin_probe(probe)


def _is_safe_cross_origin_url(text):
    return _cross_origin_probe(_probe(text))


def _js_ws_tokens(text):
    """Split the way htmx 1.9.2 does: trim and ``/\\s+/`` on the ECMAScript set."""
    return [token for token in _JS_WS.split(str(text)) if token]


def _sse_ws_directive(probe):
    """True for ``swap``/``send`` whose name matches ``[A-Za-z0-9_.-]+``."""
    keyword, sep, name = probe.partition(":")
    if keyword not in {"swap", "send"} or not sep or not name:
        return False
    return all(char in _SSE_WS_NAME_CHARS for char in name)


def _sse_ws_value_ok(text, *, cross):
    """htmx 1.9.2 splits the value on JavaScript whitespace, then ``connect:``.

    HTML entities are decoded before the split, so a character reference
    cannot glue two tokens. Only tokens that start with ``connect:`` (after
    the same noise strip as other URLs) are URL prefixes. ``swap:`` and
    ``send:`` are not URLs, and their names may not contain ``:``.
    """
    inner_ok = _cross_origin_probe if cross else _relative_same_origin_probe
    # Decode first. ``&#32;`` is a space; splitting the raw source would miss it.
    # ``_probe`` decodes again. That second decode only over-refuses, so it
    # fails closed. Leave it.
    decoded = html.unescape(str(text))
    # Tab/space between slashes is still a protocol-relative URL after the noise strip.
    if _is_protocol_relative(_probe(decoded)):
        return False
    tokens = _js_ws_tokens(decoded)
    if not tokens:
        return True
    index = 0
    while index < len(tokens):
        probe = _probe(tokens[index])
        # A space after the colon is the same noise other URL checks strip.
        if probe == "connect:" and index + 1 < len(tokens):
            nxt = _probe(tokens[index + 1])
            if not _sse_ws_directive(nxt):
                probe = "connect:" + nxt
                index += 1
        if probe.startswith("connect:"):
            inner = probe[len("connect:") :]
            if not inner or not inner_ok(inner):
                return False
        elif not _sse_ws_directive(probe) and not inner_ok(probe):
            return False
        index += 1
    return True


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
        if name in _SSE_WS_ATTRIBUTES:
            ok = _sse_ws_value_ok(text, cross=isinstance(value, CrossOriginURL))
            return text if ok else UNSAFE_URL
        if isinstance(value, CrossOriginURL):
            return text if _is_safe_cross_origin_url(text) else UNSAFE_URL
        return text if _is_same_origin_url(text) else UNSAFE_URL
    if name not in URL_ATTRIBUTES:
        return value
    # Stringify once and return that text: re-stringifying ``value`` later
    # could yield something other than what was checked.
    text = str(value)
    return text if _is_safe_url(text) else UNSAFE_URL


_unescape = {
    "quot": 34,
    "amp": 38,
    "lt": 60,
    "gt": 62,
    "nbsp": 32,
    # more here
    # http://www.w3.org/TR/html4/sgml/entities.html
    "yuml": 255,
}
str_escape = escape


def unescape(data):
    """
    unescapes html entities. the opposite of escape.
    """
    cc = re.compile(r"&(?:(?:#(\d+))|([^;]+));")

    result = []
    m = cc.search(data)
    while m:
        result.append(data[0 : m.start()])
        d = m.group(1)
        if d:
            d = int(d)
            result.append(unichr(d))
        else:
            d = _unescape.get(m.group(2), ord("?"))
            result.append(unichr(d))

        data = data[m.end() :]
        m = cc.search(data)

    result.append(data)
    return "".join(result)


_reserved = ";/?:@&=+$, "
_replace_map = dict((c, "%%%2X" % ord(c)) for c in _reserved)


def url_escape(data):
    return "".join(_replace_map.get(c, c) for c in data)


def url_unescape(data):
    return re.sub("%([0-9a-fA-F]{2})", lambda m: unichr(int(m.group(1), 16)), data)


class lazy(dom_tag):
    """
    delays function execution until rendered
    """

    def __new__(_cls, *args, **kwargs):
        """
        Need to reset this special method or else
        dom_tag will think it's being used as a dectorator.

        This means lazy() can't be used as a dectorator, but
        thinking about when you might want that just confuses me.
        """
        return object.__new__(_cls)

    def __init__(self, func, *args, **kwargs):
        super(lazy, self).__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def _render(self, sb, *a, **kw):
        r = self.func(*self.args, **self.kwargs)
        sb.append(str(r))
        return sb


# Alias: ``raw`` is the preferred public name (see below).
class dom_text(dom_tag):
    """
    Just a string. useful for inside context managers
    """

    is_pretty = False
    is_inline = False

    def __init__(self, _text, escape=True):
        self.escaped = escape
        if escape:
            self.text = str_escape(_text)
        else:
            self.text = _text
        super(dom_text, self).__init__()

    def _render(self, sb, *a, **kw):
        sb.append(self.text)
        return sb


def raw(s):
    """
    Inserts a raw string into the DOM. Unsafe.
    """
    return dom_text(s, escape=False)
