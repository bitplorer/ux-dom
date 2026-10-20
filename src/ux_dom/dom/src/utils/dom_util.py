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

from ux_dom.dom.src.concurrency import multi_tree_lock
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
    "checked_tag_name",
    "checked_comment_text",
    "checked_doctype",
    "InvalidMarkupToken",
    "InvalidNodeContext",
    "InvalidTagName",
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
    In ``<script>``, ``<!--`` becomes ``\\u003C!--`` so the parser never enters
    the script-data-escaped states (spec "restrictions for contents of script
    elements"). Both forms are valid in JS strings, JSON (``application/json``,
    ``importmap``) and u-flag regexes (unlike ``\\!``). Everything else (``<``,
    ``&``, quotes) is emitted verbatim. Callers pass the element's whole joined
    body: neutralizing children one by one misses hazards split across them.
    """
    if not isinstance(data, str):
        data = str(data)
    pattern = _RAW_TEXT_HAZARDS.get(str(tagname).lower())
    if pattern is None:
        return data

    def _sub(m):
        if m.group(1) is not None:
            return "<\\/" + m.group(1)
        return "\\u003C!--"

    return pattern.sub(_sub, data)


# Elements whose body the HTML tokenizer reads as text up to their own end tag.
# RCDATA (§13.2.5.2) decodes character references; RAWTEXT (§13.2.5.3) does
# not. ``noscript`` is RAWTEXT when scripting is on. ``script`` / ``style`` are
# ``_RAW_TEXT_HAZARDS``; ``plaintext`` has no end tag, so nothing ends it.
_RCDATA_ELEMENTS = frozenset({"textarea", "title"})
TEXT_STATE_ELEMENTS = _RCDATA_ELEMENTS | {
    "xmp", "iframe", "noembed", "noframes", "noscript",
}
# Elements whose body keeps every whitespace character: raw text, RCDATA,
# RAWTEXT, PLAINTEXT and preformatted text. Pretty render adds none there.
VERBATIM_ELEMENTS = TEXT_STATE_ELEMENTS | {
    "script", "style", "plaintext", "pre", "listing",
}
# The tokenizer folds ASCII case only, so ``re.A``.
_TEXT_STATE_END = {
    name: re.compile("</" + name, re.I | re.A) for name in TEXT_STATE_ELEMENTS
}


def checked_text_state_body(body, name):
    """The body of RCDATA / RAWTEXT element ``name`` with no ``</name`` in it.

    Text children are escaped already; this catches the rest (``style`` /
    ``script`` bodies, comments, ``raw()``) at any depth, over the joined body.
    RCDATA decodes ``&lt;``, so ``</name`` becomes ``&lt;/name``: the same
    value. RAWTEXT has no other spelling for it, so it raises
    ``InvalidNodeContext``.
    """
    end = _TEXT_STATE_END[name]
    if name in _RCDATA_ELEMENTS:
        return end.sub(lambda m: "&lt;" + m.group()[1:], body)
    if end.search(body):
        raise InvalidNodeContext(
            "<%s> is RAWTEXT: its content would end it early (</%s)" % (name, name)
        )
    return body


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
# Attributes whose value is a whole HTML document, not a URL. A string is
# sanitized by the HTML-string allowlist. A ``__html__`` opt-in (``Markup``)
# stays verbatim.
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


class InvalidTagName(ValueError):
    """A tag name that could break out of the tag (fail closed)."""


# Names without ``-``: HTML, camelCase SVG (``linearGradient``) and namespaced
# (``svg:rect``) names, ASCII only. No whitespace, quotes, ``/``, ``=`` or
# ``>``, so a name cannot add attributes or close the tag.
_TAG_NAME = re.compile(r"[A-Za-z][A-Za-z0-9._:-]*")
# Names with ``-``: the HTML spec's valid custom element name grammar
# (``[a-z] PCENChar* '-' PCENChar*``), which allows non-ASCII (``x-ñ``).
# Built-in hyphenated SVG names (``font-face``) fit it too.
_PCEN_CHARS = (
    "-._0-9a-z\u00b7\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u037d\u037f-\u1fff"
    "\u200c-\u200d\u203f-\u2040\u2070-\u218f\u2c00-\u2fef\u3001-\ud7ff"
    "\uf900-\ufdcf\ufdf0-\ufffd\U00010000-\U000effff"
)
_CUSTOM_TAG_NAME = re.compile("[a-z][%s]*-[%s]*" % (_PCEN_CHARS, _PCEN_CHARS))


def checked_tag_name(name):
    """Return ``name`` as text, or raise InvalidTagName."""
    text = str(name)
    rule = _CUSTOM_TAG_NAME if "-" in text else _TAG_NAME
    if not rule.fullmatch(text):
        raise InvalidTagName(f"invalid tag name: {text!r}")
    return text


class InvalidMarkupToken(ValueError):
    """Comment or doctype text that would end the token early (fail closed)."""


class InvalidNodeContext(ValueError):
    """A node rendered where its raw output would change context (fail closed)."""


def checked_comment_text(text):
    """Return ``text`` if it is valid HTML comment text, else raise.

    HTML spec (comments): the text must not start with ``>`` or ``->``,
    must not contain ``-->``, ``--!>`` or ``<!--``, and must not end with
    ``<!-``.
    """
    text = str(text)
    if (
        text.startswith((">", "->"))
        or "-->" in text
        or "--!>" in text
        or "<!--" in text
        or text.endswith("<!-")
    ):
        raise InvalidMarkupToken(f"invalid comment text: {text!r}")
    return text


_QUOTED = r"(?:\"[^\">]*\"|'[^'>]*')"
_DOCTYPE = re.compile(
    r"[A-Za-z][A-Za-z0-9]*"
    r"(?:\s+(?:PUBLIC\s+%s(?:\s+%s)?|SYSTEM\s+%s))?" % (_QUOTED, _QUOTED, _QUOTED),
    re.IGNORECASE,
)


def checked_doctype(text):
    """Return ``text`` if it is ``name [PUBLIC "id" ["id"] | SYSTEM "id"]``.

    The name is ASCII alphanumeric; identifiers are quoted and contain no
    ``>`` or their own quote, so nothing can close the doctype early.
    """
    text = str(text)
    if not _DOCTYPE.fullmatch(text):
        raise InvalidMarkupToken(f"invalid doctype: {text!r}")
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

    HTML attributes (``srcdoc``) run a string through the same allowlist
    sanitizer as ``defHTML``. A ``__html__`` value (``Markup``) is still the
    verbatim opt-in (it is still attribute-escaped by the renderer).

    For checked attributes the return value is always the ``str`` that was
    checked, so the renderer never stringifies the original object again.
    """
    name = str(attribute).lower()
    if name in HTML_ATTRIBUTES:
        return _srcdoc_value(value)
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


def _srcdoc_value(value):
    """Sanitize string srcdoc with the HTML-string allowlist.

    Local import: ``html_string`` imports this module, so a top-level import
    would cycle.
    """
    from ux_dom.dom.src.html_string import _sanitized_html

    # ``__html__`` first: MarkupSafe ``Markup`` is a ``str`` and is trusted.
    html_method = getattr(value, "__html__", None)
    if callable(html_method):
        return str(html_method())
    if isinstance(value, str):
        return _sanitized_html(value)
    return UNSAFE_URL


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
        if isinstance(r, dom_tag):
            # A tag renders as a child at this position: same layout arguments,
            # and its context checks (a CSS rule outside <style>, #81) see
            # this node's parent. The cycle guard gets this node's ancestors
            # only: a node rendered elsewhere in the tree is reuse, not a cycle.
            ancestors: set = set()
            node = self
            while node is not None and id(node) not in ancestors:
                ancestors.add(id(node))
                node = node.parent
            with multi_tree_lock(r):
                parent, r.parent = r.parent, self.parent
                try:
                    text = "".join(r._render([], *a, **{**kw, "_seen": ancestors}))
                finally:
                    r.parent = parent
        else:
            text = str(r)
        # A str result is text, like a str child. Tags, raw() and Markup
        # (``__html__``) are HTML already. Inside script / style the parent
        # neutralizes breakouts over the joined body at render time.
        trusted = isinstance(r, dom_tag) or callable(getattr(r, "__html__", None))
        if not trusted and not getattr(type(self.parent), "raw_text", None):
            text = str_escape(text)
        sb.append(text)
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
