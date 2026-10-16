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
    "unescape",
    "url_escape",
    "url_unescape",
    "lazy",
    "dom_text",
    "raw",
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


def escape(data, quote=True):  # stolen from std lib cgi
    """Escape HTML special chars; strip C0 controls in attribute mode."""
    if not isinstance(data, str):
        data = str(data)
    if quote:
        data = _CTRL_ATTR.sub("", data)
    data = data.replace("&", "&" + "amp;")  # Must be done first!
    data = data.replace("<", "&" + "lt;")
    data = data.replace(">", "&" + "gt;")
    if quote:
        data = data.replace('"', "&" + "quot;")
    return data


# URL-bearing attributes. A script-capable scheme here is an XSS sink, so the
# renderer fails closed: the value becomes UNSAFE_URL (inert, like Closure's
# "about:invalid#zClosurez"). Applies to every render path, including
# attributes marked unescaped, because no caller needs an executable URL.
URL_ATTRIBUTES = frozenset(
    {
        "href", "src", "action", "formaction", "xlink:href", "poster",
        "cite", "background", "data", "codebase", "longdesc",
        "manifest", "ping", "icon", "archive", "usemap", "profile",
        "lowsrc", "dynsrc", "hx-get", "hx-post", "hx-put", "hx-patch",
        "hx-delete",
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
_SAFE_DATA_URL = re.compile(r"data:image/(?:png|jpeg|jpg|gif|webp)(?:[;,]|$)")


def _is_safe_url(text):
    """True for relative URLs, allow-listed schemes, and raster data: images."""
    # Browsers decode entities before parsing the URL; check what they see.
    probe = _URL_NOISE.sub("", html.unescape(text)).lower()
    head = re.split(r"[/?#]", probe, maxsplit=1)[0]
    if ":" not in head:
        return True  # relative: "/a", "a/b", "?q", "#f", "//host/x"
    scheme = head.split(":", 1)[0]
    if scheme == "data":
        return _SAFE_DATA_URL.match(probe) is not None
    return scheme in _SAFE_SCHEMES


def safe_attr_value(attribute, value):
    """Return ``value``, or UNSAFE_URL if it is not safe for ``attribute``.

    URL attributes keep only relative URLs, ``http``, ``https``, ``mailto``,
    ``tel`` and ``data:image/{png,jpeg,gif,webp}`` (never SVG). The check runs
    on ``str(value)`` after HTML entities are decoded and the C0 controls and
    spaces that browsers ignore inside a scheme are removed.

    HTML attributes (``srcdoc``) are refused unless the value implements
    ``__html__``; then that HTML is returned (it is still attribute-escaped).
    """
    name = str(attribute).lower()
    if name in HTML_ATTRIBUTES:
        html_method = getattr(value, "__html__", None)
        return str(html_method()) if callable(html_method) else UNSAFE_URL
    if name not in URL_ATTRIBUTES:
        return value
    return value if _is_safe_url(str(value)) else UNSAFE_URL


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
