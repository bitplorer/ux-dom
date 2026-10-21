"""A simple but complete HTML to Abstract Syntax Tree (AST) parser.

The AST can also reproduce the HTML text.

Example::

    >> text = '<div class="note"><p>text</p></div>'
    >> ast = tokenize_html(text)
    >> list(ast.walk(include_self=True))
    [Root(''), Tag('div', {'class': 'note'}), Tag('p'), Data('text')]
    >> str(ast)
    '<div class="note"><p>text</p></div>'
    >> str(ast[0][0])
    '<p>text</p>'

Optional end tags are implied as a browser implies them (``Tree``).

"""

from __future__ import annotations

import inspect
import itertools
import re
from collections import abc, deque
from html import escape, unescape
from html.parser import HTMLParser
from html.parser import commentclose  # type: ignore[attr-defined]
import typing as T
from typing import Any, Callable, Iterable, Iterator

from ux_dom.dom.src.utils.dom_util import FIRST_LF_DROPPED, LEADING_LF


class Attribute(dict):
    """This class holds the tags's attributes."""

    def __getitem__(self, key: str) -> str:
        """If self doesn't have the key it returns ''."""
        return self.get(key, "")

    @property
    def classes(self) -> list[str]:
        """Return 'class' attribute as list."""
        raw = self.get("class") or ""
        if not isinstance(raw, str):
            raw = str(raw)
        return [c for c in raw.split() if c]

    def __str__(self) -> str:
        """Return a htmlized representation for attributes."""
        parts = []
        for key, value in self.items():
            if value is None or value is True:
                parts.append(f"{key}")
            elif value is False:
                continue
            else:
                parts.append(f'{key}="{value}"')
        return " ".join(parts)


class Element(abc.MutableSequence):
    """An Element of the xml/html document.

    All xml/html entities inherit from this class.
    """

    # ``"svg"`` / ``"math"`` for an element the tree puts in foreign content.
    namespace = "html"
    # Elements above it in the tree (``Tree`` keeps it <= ``MAX_TREE_DEPTH``).
    depth = 0

    def __init__(self, name: str = "", attr: dict | None = None) -> None:
        """Initialise the element."""
        self.name = name
        self.attrs: Attribute = Attribute(attr or {})
        self._parent: Element | None = None
        self._children: list[Element] = []

    @property
    def parent(self) -> Element | None:
        """Return parent."""
        return self._parent

    @property
    def children(self) -> list[Element]:
        """Return copy of children."""
        return self._children[:]

    def reset_children(self, children: list[Element], deepcopy: bool = False):
        new_children = []
        for i, item in enumerate(children):
            assert isinstance(item, Element)
            if deepcopy:
                item = item.deepcopy()
            if item._parent is None:
                item._parent = self
            elif item._parent != self:
                raise AssertionError(f"different parent already set for item {i}")
            new_children.append(item)
        self._children = new_children

    def __getitem__(self, index: int) -> Element:  # type: ignore[override]
        return self._children[index]

    def __setitem__(self, index: int, value: Element):  # type: ignore[override]
        # Param name ``value`` matches MutableSequence.__setitem__(index, value)
        assert isinstance(value, Element)
        if value._parent is not None and value._parent != self:
            raise AssertionError(f"different parent already set for: {value!r}")
        value._parent = self
        return self._children.__setitem__(index, value)

    def __delitem__(self, index: int):  # type: ignore[override]
        return self._children.__delitem__(index)

    def __len__(self) -> int:
        return self._children.__len__()

    def __iter__(self) -> Iterator[Element]:
        yield from self._children

    def insert(self, index: int, value: Element):
        # Param name ``value`` matches MutableSequence.insert(index, value)
        assert isinstance(value, Element)
        if value._parent is not None and value._parent != self:
            raise AssertionError(f"different parent already set for: {value!r}")
        value._parent = self
        return self._children.insert(index, value)

    def deepcopy(self) -> Element:
        """Recursively copy and remove parent."""
        _copy = self.__class__(self.name, self.attrs)
        for child in self:
            _copy_child = child.deepcopy()
            _copy.append(_copy_child)
        return _copy

    def __repr__(self) -> str:
        text = f"{self.__class__.__name__}({self.name!r}"
        if self.attrs:
            text += f", {self.attrs!r}"
        text += ")"
        return text

    def render(
        self,
        tag_overrides: dict[str, Callable[[Element, dict], str]] | None = None,
        **kwargs,
    ) -> str:
        """Returns a HTML string representation of the element.

        :param tag_overrides: Provide a dictionary of render function
            for specific tag names, to override the normal render format

        """
        raise NotImplementedError

    def __str__(self) -> str:
        return self.render()

    def __eq__(self, item: Any) -> bool:
        return item is self

    def walk(self, include_self: bool = False) -> Iterator[Element]:
        """Walk through the xml/html AST."""
        if include_self:
            yield self
        for child in self:
            yield child
            yield from child.walk()

    def strip(self, inplace: bool = False, recurse: bool = False) -> Element:
        """Return copy with all `Data` tokens
        that only contain whitespace / newlines removed.
        """
        element = self
        if not inplace:
            element = self.deepcopy()
        element.reset_children(
            [
                e
                for e in element.children
                if not (isinstance(e, Data) and e.data.strip() == "")
            ]
        )
        if recurse:
            for child in element:
                child.strip(inplace=True, recurse=True)
        return element

    def find(
        self,
        identifier: str | type[Element],
        attrs: dict | None = None,
        classes: Iterable[str] | None = None,
        include_self: bool = False,
        recurse: bool = True,
    ) -> Iterator[Element]:
        """Find all elements that match name and specific attributes."""
        iterator = self.walk() if recurse else self
        if include_self:
            iterator = itertools.chain([self], iterator)
        if inspect.isclass(identifier):
            test_func = lambda c: isinstance(c, identifier)  # noqa: E731
        else:
            test_func = lambda c: c.name == identifier  # noqa: E731
        classes = set(classes) if classes is not None else classes
        for child in iterator:
            if test_func(child):
                if classes is not None and not classes.issubset(child.attrs.classes):
                    continue
                for key, value in (attrs or {}).items():
                    if child.attrs[key] != value:
                        break
                else:
                    yield child


class Root(Element):
    """The root of the AST tree."""

    def render(self, **kwargs) -> str:  # type: ignore[override]
        """Returns a string HTML representation of the structure."""
        return "".join(child.render(**kwargs) for child in self)


class Tag(Element):
    """Represent xml/html tags under the form: <name key="value" ...> ... </name>."""

    def render(
        self,
        tag_overrides: dict[str, Callable[[Element, dict], str]] | None = None,
        **kwargs,
    ) -> str:
        if tag_overrides and self.name in tag_overrides:
            return tag_overrides[self.name](self, tag_overrides)
        body = "".join(
            child.render(tag_overrides=tag_overrides, **kwargs) for child in self
        )
        if (
            LEADING_LF.match(body)
            and self.namespace == "html"
            and self.name in FIRST_LF_DROPPED
        ):
            body = "\n" + body  # the parser drops this one (``Tree.nest_terminal``)
        open_tag = f"<{self.name}{' ' if self.attrs else ''}{self.attrs}>"
        return f"{open_tag}{body}</{self.name}>"


class XTag(Element):
    """Represent XHTML style tags with no children, like `<img src="t.gif" />`"""

    def render(
        self,
        tag_overrides: dict[str, Callable[[Element, dict], str]] | None = None,
        **kwargs,
    ) -> str:
        if tag_overrides is not None and self.name in tag_overrides:
            return tag_overrides[self.name](self, tag_overrides)
        return f"<{self.name}{' ' if self.attrs else ''}{self.attrs}/>"


class VoidTag(Element):
    """Represent tags with no children, only start tag, like `<img src="t.gif" >`"""

    def render(self, **kwargs) -> str:  # type: ignore[override]
        return f"<{self.name}{' ' if self.attrs else ''}{self.attrs}>"


class TerminalElement(Element):
    def __init__(self, data: str):
        super().__init__("")
        self.data: str = data

    def __repr__(self) -> str:
        text = self.data
        if len(text) > 20:
            text = text[:17] + "..."
        return f"{self.__class__.__name__}({text!r})"

    def deepcopy(self) -> TerminalElement:
        """Copy and remove parent."""
        _copy = self.__class__(self.data)
        return _copy


class Data(TerminalElement):
    """Represent data inside xml/html documents, like raw text."""

    def render(self, **kwargs) -> str:  # type: ignore[override]
        return self.data


class Declaration(TerminalElement):
    """Represent declarations, like `<!DOCTYPE html>`"""

    def render(self, **kwargs) -> str:  # type: ignore[override]
        return f"<!{self.data}>"


class Comment(TerminalElement):
    """Represent HTML comments"""

    def render(self, **kwargs) -> str:  # type: ignore[override]
        return f"<!--{self.data}-->"


class Pi(TerminalElement):
    """Represent processing instructions like `<?xml-stylesheet ?>`"""

    def render(self, **kwargs) -> str:  # type: ignore[override]
        return f"<?{self.data}>"


class Char(TerminalElement):
    """Represent character codes like: `&#0`"""

    def render(self, **kwargs) -> str:  # type: ignore[override]
        if _CHARREF_NAME.fullmatch(self.data):
            return f"&#{self.data};"
        return "&amp;#" + escape(self.data, quote=False)


class Entity(TerminalElement):
    """Represent entities like `&amp`"""

    def render(self, **kwargs) -> str:  # type: ignore[override]
        if _ENTITYREF_NAME.fullmatch(self.data):
            return f"&{self.data};"
        return "&amp;" + escape(self.data, quote=False)


def _normalize_attrs(attrs) -> dict:
    """HTMLParser may pass list[tuple[str, str|None]]; coerce to dict."""
    if attrs is None:
        return {}
    if isinstance(attrs, dict):
        return {str(k): ("" if v is None else v) for k, v in attrs.items()}
    out = {}
    for item in attrs:
        if not item:
            continue
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            k, v = item[0], item[1]
            out[str(k)] = "" if v is None else v
        elif isinstance(item, (list, tuple)) and len(item) == 1:
            out[str(item[0])] = ""
    return out


# Tree construction (HTML spec §13.2.6, WHATWG). The tokenizer is the stdlib
# ``HTMLParser``; this builds the tree a browser builds from its tokens for a
# fragment: implied end tags (``<p>a<p>b`` is two paragraphs, ``<li>a<li>b``
# two items), the table modes, breakout from foreign content (§13.2.6.5), and
# Chromium's depth limit. Each set below is the spec's list it is named for.
#
# Left out, so the tree can still differ from a browser's: the adoption agency
# and the list of active formatting elements (``<b>1<p>2</b>3``), foster
# parenting (content directly in a ``<table>``), the form element pointer
# (only an open ``form`` makes a nested ``<form>`` be ignored; the pointer
# outlives the element, which would hold state across a stream cut), and the
# context element: the fragment may be inserted anywhere, so ``<tr>`` with no
# table is kept, where ``innerHTML`` on a ``<div>`` drops it.

# §13.2.4.2 "special" category (HTML namespace).
_SPECIAL = frozenset(
    """address applet area article aside base basefont bgsound blockquote body
    br button caption center col colgroup dd details dir div dl dt embed
    fieldset figcaption figure footer form frame frameset h1 h2 h3 h4 h5 h6
    head header hgroup hr html iframe img input keygen li link listing main
    marquee menu meta nav noembed noframes noscript object ol p param
    plaintext pre script search section select source style summary table
    tbody td template textarea tfoot th thead title tr track ul wbr
    xmp""".split()
)
# Foreign elements that are special and bound every scope: MathML text
# integration points plus ``annotation-xml``, and SVG HTML integration points.
_FOREIGN_SPECIAL = {
    "math": frozenset({"mi", "mo", "mn", "ms", "mtext", "annotation-xml"}),
    "svg": frozenset({"foreignobject", "desc", "title"}),
}
# §13.2.4.2 "has an element in scope" boundaries (HTML namespace). ``select``
# is one since the 2025 select parser change (whatwg/html#10548), as Chromium
# parses: ``<p><select><p>`` nests the second ``p``.
_SCOPE = frozenset(
    "applet caption html table td th marquee object select template".split()
)
_HEADINGS = frozenset("h1 h2 h3 h4 h5 h6".split())
# §13.2.6.4.7 "in body": start tags that close a ``p`` in button scope.
_CLOSES_P = _HEADINGS | frozenset(
    """address article aside blockquote center details dialog dir div dl
    fieldset figcaption figure footer form header hgroup hr listing main menu
    nav ol p plaintext pre search section summary table ul xmp""".split()
)
# §13.2.6.3 "generate implied end tags".
_IMPLIED_END = frozenset("dd dt li optgroup option p rb rp rt rtc".split())
# §13.2.6.4.7 end tags that close their element only when it is in scope.
_FORMATTING = frozenset(
    "a b big code em font i nobr s small strike strong tt u".split()
)
_TABLE_PARTS = frozenset("caption col colgroup tbody td tfoot th thead tr".split())
_ROW_GROUPS = frozenset({"tbody", "thead", "tfoot"})
# Elements whose nearest one on the stack picks the table insertion mode
# (§13.2.4.1, "reset the insertion mode appropriately").
_TABLE_CONTEXT = _TABLE_PARTS - {"col"} | {"table", "template"}
# §13.2.6.5: start tags that pop foreign content back to HTML.
_BREAKOUT = frozenset(
    """b big blockquote body br center code dd div dl dt em embed h1 h2 h3 h4
    h5 h6 head hr i img li listing menu meta nobr ol p pre ruby s small span
    strong strike sub sup table tt u ul var""".split()
)
# A self-closing start tag (``<div/>``) opens an HTML element as a plain one
# does. Void and foreign elements end there, and so do the raw text and RCDATA
# elements: the tokenizer reads no raw text after ``/>``, so their content
# would otherwise be parsed as markup inside them.
_SELF_CLOSING_ENDS = frozenset(
    HTMLParser.CDATA_CONTENT_ELEMENTS
    + getattr(HTMLParser, "RCDATA_CONTENT_ELEMENTS", ("textarea", "title"))
    + ("noscript", "plaintext", "svg", "math")
)
# Chromium attaches an element opened below this many open elements to the
# parent of the current node instead (``kMaximumHTMLParserDOMTreeDepth``).
# Measured in Chromium: ``<i>`` x 600 in ``innerHTML`` gives a tree 512
# elements deep, the last 89 of them siblings. The tree here counts the
# depth itself rather than the open elements, which is the same number
# except after ``</form>`` (it leaves the elements inside open), so a parsed
# tree is never deeper than this, whatever the input.
MAX_TREE_DEPTH = 512


def _is_integration_point(namespace: str, name: str, attrs: dict) -> bool:
    if name in _FOREIGN_SPECIAL.get(namespace, ()):
        if name != "annotation-xml":
            return True
        encoding = str(attrs.get("encoding", "")).lower()
        return encoding in ("text/html", "application/xhtml+xml")
    return False


def _stack_keys(node: Element) -> tuple[str, ...]:
    """The stack indexes ``node`` is listed in while it is open (see ``Tree``)."""
    name, ns = node.name, node.namespace
    if ns != "html":
        keys = [f"{ns}:{name}"]
        if name in _FOREIGN_SPECIAL[ns]:
            keys += ["special", "scope", "scope:li", "scope:button"]
            keys += ["stop:li", "stop:dd"]
        if _is_integration_point(ns, name, node.attrs):
            keys.append("ip")
        return tuple(keys)
    keys = [f"n:{name}", "html"]
    if name in _SPECIAL:
        keys.append("special")
        if name not in ("address", "div", "p", "li"):
            keys.append("stop:li")
        if name not in ("address", "div", "p", "dd", "dt"):
            keys.append("stop:dd")
    if name in _SCOPE:
        keys += ["scope", "scope:li", "scope:button"]
    elif name in ("ol", "ul"):
        keys.append("scope:li")
    elif name == "button":
        keys.append("scope:button")
    if name in ("table", "template"):
        keys.append("scope:table")
    if name in _TABLE_CONTEXT:
        keys.append("table")
    if name in _HEADINGS:
        keys.append("heading")
    return tuple(keys)


# The root stands for the ``html`` element: special, and a boundary of every
# scope.
_ROOT_KEYS = (
    "special stop:li stop:dd scope scope:li scope:button scope:table html "
    "table".split()
)


class Tree:
    """The engine class to generate the AST tree.

    ``stack`` is the stack of open elements (the root first). Each spec query
    on it ("a ``p`` in button scope", "the nearest special element") is a
    comparison of two positions: ``_at`` keeps, per key from
    ``_stack_keys``, the positions of the open elements listed under it, so
    every query is O(1) and building the tree is linear in its size.
    """

    def __init__(self, name: str = ""):
        """Initialise Tree"""
        self.name = name
        self.clear()

    def clear(self):
        """Clear the outmost and stack for a new parsing."""
        self.outmost = Root(self.name)
        self.stack: list[Element] = [self.outmost]
        self._at: dict[str, list[int]] = {key: [0] for key in _ROOT_KEYS}
        # Set by a start tag whose next token, if an LF, is dropped.
        self._drop_lf = False

    def last(self) -> Element:
        """Return the last pointer which point to the actual tag scope."""
        return self.stack[-1]

    def _push(self, node: Element) -> None:
        index = len(self.stack)
        self.stack.append(node)
        for key in _stack_keys(node):
            self._at.setdefault(key, []).append(index)

    def _pop(self) -> None:
        node = self.stack.pop()
        for key in _stack_keys(node):
            self._at[key].pop()

    def _pop_to(self, index: int) -> None:
        """Pop the element at ``index`` and every element above it."""
        while len(self.stack) > max(index, 1):
            self._pop()

    def _pos(self, key: str) -> int:
        """Position of the nearest open element listed under ``key``, or -1."""
        positions = self._at.get(key)
        return positions[-1] if positions else -1

    def _in_scope(self, key: str, scope: str = "scope") -> bool:
        return self._pos(key) >= self._pos(scope)

    def _current_is(self, *names: str) -> bool:
        node = self.stack[-1]
        return node.namespace == "html" and node.name in names

    def _generate_implied_end_tags(self, but: str = "") -> None:
        while self._current_is(*_IMPLIED_END) and self.stack[-1].name != but:
            self._pop()

    def _close_p(self) -> None:
        if self._in_scope("n:p", "scope:button"):
            self._pop_to(self._pos("n:p"))

    def _insert(self, kind, name: str, attrs, namespace: str = "html") -> Element:
        parent = self.stack[-1]
        if parent.depth >= MAX_TREE_DEPTH:
            parent = T.cast(Element, parent.parent)
        item = kind(name, _normalize_attrs(attrs))
        item.namespace = namespace
        item.depth = parent.depth + 1
        parent.append(item)
        if kind is Tag:
            self._push(item)
            self._drop_lf = namespace == "html" and name in FIRST_LF_DROPPED
        return item

    def start(self, name: str, attrs, *, void: bool = False, self_closing=False):
        """A start tag: close what it implies, then insert it."""
        self._drop_lf = False
        current = self.stack[-1]
        if current.namespace != "html" and not self._html_at(current, name):
            if not (
                name in _BREAKOUT
                or name == "font"
                and {"color", "face", "size"} & set(_normalize_attrs(attrs))
            ):
                kind = XTag if self_closing else Tag
                self._insert(kind, name, attrs, current.namespace)
                return
            self._pop_to(max(self._pos("html"), self._pos("ip")) + 1)
        if not self._table_start(name) or not self._body_start(name):
            return
        namespace = name if name in ("svg", "math") else "html"
        if self_closing and (void or namespace != "html" or name in _SELF_CLOSING_ENDS):
            self._insert(XTag, name, attrs, namespace)
        elif void:
            self._insert(VoidTag, name, attrs)
        else:
            self._insert(Tag, name, attrs, namespace)

    @staticmethod
    def _html_at(node: Element, name: str) -> bool:
        """Whether a start tag at foreign ``node`` follows the HTML rules."""
        if not _is_integration_point(node.namespace, node.name, node.attrs):
            return False
        return not (
            node.namespace == "math"
            and node.name != "annotation-xml"
            and name in ("mglyph", "malignmark")
        )

    def _table_start(self, name: str) -> bool:
        """The table insertion modes (§13.2.6.4.9-15) for a start tag.

        Returns ``False`` when the tag is ignored. The mode comes from the
        nearest open table element, as "reset the insertion mode" picks it.
        """
        while name in _TABLE_PARTS or name == "table":
            index = self._pos("table")
            mode = self.stack[index].name if index else ""
            if mode in ("td", "th"):
                if name == "table":
                    return True
                self._pop_to(index)  # close the cell
            elif name == "table" and mode in ("tr", *_ROW_GROUPS):
                self._pop_to(self._pos("n:table"))  # a table here closes the table
            elif mode == "tr":
                if name in ("td", "th"):
                    self._pop_to(index + 1)
                    return True
                self._pop_to(index)
            elif mode in _ROW_GROUPS:
                if name == "tr":
                    self._pop_to(index + 1)
                    return True
                self._pop_to(index + 1)
                if name in ("td", "th"):
                    self._insert(Tag, "tr", {})
                else:
                    self._pop_to(index)
            elif mode == "caption":
                if name == "table":
                    return True
                self._pop_to(index)
            elif mode == "colgroup":
                if name == "col":
                    return True
                self._pop_to(index)
            elif mode == "table":
                self._pop_to(index + 1)
                if name in ("caption", "colgroup", "tbody", "tfoot", "thead"):
                    return True
                if name == "col":
                    self._insert(Tag, "colgroup", {})
                elif name in ("td", "th", "tr"):
                    self._insert(Tag, "tbody", {})
                else:
                    self._pop_to(index)  # a table in a table closes it
            else:
                return True
        return True

    def _body_start(self, name: str) -> bool:
        """The "in body" rules (§13.2.6.4.7) that close elements before a
        start tag. Returns ``False`` when the tag is ignored."""
        if name == "form" and self._pos("n:form") > self._pos("n:template"):
            return False
        if name in _CLOSES_P:
            self._close_p()
            if name in _HEADINGS and self._current_is(*_HEADINGS):
                self._pop()
            if name == "hr" and self._in_scope("n:select"):
                self._generate_implied_end_tags()
        elif name == "li":
            if self._pos("n:li") > self._pos("stop:li"):
                self._pop_to(self._pos("n:li"))
            self._close_p()
        elif name in ("dd", "dt"):
            index = max(self._pos("n:dd"), self._pos("n:dt"))
            if index > self._pos("stop:dd"):
                self._pop_to(index)
            self._close_p()
        elif name == "button":
            if self._in_scope("n:button"):
                self._pop_to(self._pos("n:button"))
        elif name in ("select", "input", "keygen"):
            if self._in_scope("n:select"):
                self._pop_to(self._pos("n:select"))
                return name != "select"
        elif name in ("option", "optgroup"):
            if self._in_scope("n:select"):
                self._generate_implied_end_tags(but="optgroup" if name == "option" else "")
            elif self._current_is("option"):
                self._pop()
        elif name in ("rb", "rtc", "rp", "rt"):
            if self._in_scope("n:ruby"):
                self._generate_implied_end_tags(but="rtc" if name in ("rp", "rt") else "")
        elif name == "body" and self._current_is("head"):
            self._pop()
        return True

    def end(self, name: str) -> None:
        """An end tag: close the element it names where the spec does."""
        self._drop_lf = False
        if self.stack[-1].namespace != "html":
            index = max(self._pos(f"svg:{name}"), self._pos(f"math:{name}"))
            if index > self._pos("html"):
                self._pop_to(index)
                return
            if name in ("br", "p"):  # §13.2.6.5: these break out too
                self._pop_to(max(self._pos("html"), self._pos("ip")) + 1)
        if self._current_is("colgroup") and name not in ("colgroup", "col"):
            self._pop()  # §13.2.6.4.12: any other end tag closes the colgroup
        if name == "p":
            if not self._in_scope("n:p", "scope:button"):
                self._insert(XTag, "p", {})  # ``</p>`` alone is ``<p></p>``
            self._close_p()
        elif name == "br":
            self._insert(VoidTag, "br", {})
        elif name == "li":
            if self._in_scope("n:li", "scope:li"):
                self._pop_to(self._pos("n:li"))
        elif name in _HEADINGS:
            if self._in_scope("heading"):
                self._pop_to(self._pos("heading"))
        elif name in _TABLE_PARTS or name == "table":
            if self._in_scope(f"n:{name}", "scope:table"):
                self._pop_to(self._pos(f"n:{name}"))
        elif name == "form":
            if self._in_scope("n:form"):
                # The form leaves the stack; what is open inside it stays
                # open. Each element re-pushed was opened after the form, so
                # the work is bounded by the input.
                self._generate_implied_end_tags()
                index = self._pos("n:form")
                above = self.stack[index + 1 :]
                self._pop_to(index)
                for node in above:
                    self._push(node)
        elif name in ("html", "head", "body", "template"):
            if self._pos(f"n:{name}") > 0:
                self._pop_to(self._pos(f"n:{name}"))
        elif name in _SPECIAL or name in _FORMATTING:
            if self._in_scope(f"n:{name}"):
                self._pop_to(self._pos(f"n:{name}"))
        elif self._pos(f"n:{name}") > self._pos("special"):
            self._pop_to(self._pos(f"n:{name}"))  # "any other end tag"

    def nest_terminal(self, klass: type[TerminalElement], data: str):
        """Nest the data onto the tree.

        An LF right after a ``pre``, ``listing`` or ``textarea`` start tag is
        dropped (§13.2.6.4.7), written or as a reference (``&#10;``); the
        renderer writes one more LF before a body that starts with one.
        """
        if self._drop_lf:
            self._drop_lf = False
            if klass is Data and data.startswith("\n"):
                data = data[1:]
            elif klass in (Char, Entity):
                lead = "&#" if klass is Char else "&"
                if unescape(f"{lead}{data};") == "\n":
                    return
            if not data:
                return
        top = self.last()
        item = klass(data)
        top.append(item)


class HtmlToAst(HTMLParser):
    """The tokenizer class."""

    # see https://html.spec.whatwg.org/multipage/syntax.html#void-elements
    void_elements = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self, name: str = "", convert_charrefs: bool = False):
        super().__init__(convert_charrefs=convert_charrefs)
        self.struct = Tree(name)

    def feed(self, data: str) -> Root:  # type: ignore[override]
        """Parse the source string (param name matches ``HTMLParser.feed``).

        Newlines are normalized first, as a browser does before it parses:
        CRLF and a lone CR are LF, in text, raw text and attributes.
        """
        self.struct.clear()
        data = data.replace("\r\n", "\n").replace("\r", "\n")
        super().feed(_finish_numeric_references(data, keep_style=True))
        return self.struct.outmost

    def handle_starttag(self, tag: str, attrs):  # type: ignore[override]
        """When found an opening tag then nest it onto the tree."""
        self.struct.start(tag, attrs, void=tag in self.void_elements)

    def handle_startendtag(self, tag: str, attrs):  # type: ignore[override]
        """``<tag/>``: the flag ends only void, foreign and raw text elements."""
        self.struct.start(
            tag, attrs, void=tag in self.void_elements, self_closing=True
        )

    def handle_endtag(self, tag: str):  # type: ignore[override]
        """When found a closing tag then makes it point to the right scope."""
        if tag == "br" or tag not in self.void_elements:
            self.struct.end(tag)

    def handle_data(self, data: str):  # type: ignore[override]
        """Nest data onto the tree."""
        self.struct.nest_terminal(Data, data)

    def handle_decl(self, decl: str):  # type: ignore[override]
        self.struct.nest_terminal(Declaration, decl)

    def unknown_decl(self, data: str):  # type: ignore[override]
        self.struct.nest_terminal(Declaration, data)

    def handle_charref(self, name: str):  # type: ignore[override]
        self._reference(Char, _CHARREF_NAME, "&#", name)

    def handle_entityref(self, name: str):  # type: ignore[override]
        self._reference(Entity, _ENTITYREF_NAME, "&", name)

    def _reference(self, kind, valid: re.Pattern[str], lead: str, name: str):
        """Keep only a well-formed reference name; the rest is plain text.

        CPython 3.14.1+ ``close`` passes the whole unparsed tail after an
        unfinished ``&#62b`` as the name, markup included. Plain text is
        escaped by the sanitizer, so that tail can never become markup.
        """
        match = valid.match(name)
        if match is None:
            self.struct.nest_terminal(Data, lead + name)
            return
        self.struct.nest_terminal(kind, match.group())
        if match.end() < len(name):
            self.struct.nest_terminal(Data, name[match.end() :])

    def handle_pi(self, data: str):  # type: ignore[override]
        self.struct.nest_terminal(Pi, data)

    def handle_comment(self, data: str):  # type: ignore[override]
        self.struct.nest_terminal(Comment, data)

    def close(self) -> None:
        """Finish the input, keeping a reference that ends it (``AT&T``).

        A tail held at ``&#`` (only possible when a ``<style`` lookalike
        hid it from ``feed``) is finished in one more linear pass. A named
        reference at the very end is reported here because Python 3.14.0's
        ``close`` drops its ``&`` (3.14.1+ reports it).
        """
        if self.rawdata.startswith("&#"):
            rest, self.rawdata = self.rawdata, ""
            HTMLParser.feed(self, _finish_numeric_references(rest, keep_style=False))
        match = _TRAILING_ENTITY.fullmatch(self.rawdata)
        if match:
            self.rawdata = ""
            self.handle_entityref(match.group(1))
        super().close()


_CHARREF = r"[0-9]+|[xX][0-9a-fA-F]+"
_ENTITYREF = r"[a-zA-Z][-.a-zA-Z0-9]*"
_CHARREF_NAME = re.compile(_CHARREF)
_ENTITYREF_NAME = re.compile(_ENTITYREF)
_TRAILING_ENTITY = re.compile(f"&({_ENTITYREF})")

# A browser ends a numeric reference at the first character that cannot
# continue it (``&#62b`` is ``>`` then ``b``) and shows a bare ``&#`` as
# text. The stdlib parser instead holds the rest of the input at such a
# reference (3.14.1+) or emits ``&#`` as text and carries on (3.14.0). So
# they are finished before parsing, in one linear pass, and every version
# sees only finished references. ``<style>`` text is raw and stays verbatim.
_NUMERIC_REFERENCE = (
    r"|&#(?P<dec>[0-9]+)(?![0-9;])"
    r"|&#(?P<hex>[xX][0-9a-fA-F]+)(?![0-9a-fA-F;])"
    r"|&#(?![0-9]|[xX][0-9a-fA-F])"
)
_UNFINISHED_NUMERIC = {
    True: re.compile(
        r"(?P<style><style\b[^>]*(?:>|\Z)(?:[^<]+|<(?!/style))*)"
        + _NUMERIC_REFERENCE,
        re.IGNORECASE,
    ),
    False: re.compile(r"(?P<style>(?!))" + _NUMERIC_REFERENCE),
}


def _finish_numeric_reference(match: re.Match[str]) -> str:
    if match.group("style") is not None:
        return match.group()
    name = match.group("dec") or match.group("hex")
    return f"&#{name};" if name else "&amp;#"


def _finish_numeric_references(text: str, *, keep_style: bool) -> str:
    if "&#" not in text:
        return text
    return _UNFINISHED_NUMERIC[keep_style].sub(_finish_numeric_reference, text)


def tokenize_html(text: str, name: str = "", convert_charrefs: bool = False) -> Root:
    if text is None:
        text = ""
    elif not isinstance(text, str):
        text = str(text)
    parser = HtmlToAst(name, convert_charrefs=convert_charrefs)
    parser.feed(text)
    parser.close()
    return parser.struct.outmost


# A cut must end every reference: ``&notin;`` cut after ``&not`` parses as
# ``¬in;``. CR is left out because CRLF is one newline.
_CUT_AFTER = frozenset(">;\t\n\f ")
# References never change the tree, so the cut finder reads ``&`` as an
# ordinary character. That keeps it from holding the rest of the input at an
# unfinished ``&#62b`` as the stdlib parser does (see ``close``).
_NO_REFERENCES = str.maketrans("&", "\x01")
# The ``<style`` region of ``_UNFINISHED_NUMERIC[True]``, in two steps.
_STYLE_START = re.compile(r"<style\b", re.IGNORECASE)
_STYLE_END = re.compile(r"</style", re.IGNORECASE)


class HtmlCuts(HtmlToAst):
    """Where a growing HTML string can be cut without changing its parse (#121).

    This is the tokenizer itself, fed one piece at a time. ``cut`` is the
    last offset where everything before it is finished top-level nodes: no
    open element, no held markup, no raw-text mode, and a character from
    ``_CUT_AFTER`` just before it. The sanitizer works one top-level node at a
    time (``defHTML``), so sanitizing the text on each side of a cut gives the
    same output as sanitizing the whole. Nodes before a cut are discarded, so
    memory is the text since the last cut.

    Two places where the whole string decides later than a prefix are not
    cuts: a ``<!-->`` comment before any ``-->`` arrives (see
    ``parse_comment``), and the ``<style`` regions in which
    ``_finish_numeric_references`` keeps references as written, which also
    open where the tokenizer sees no raw text (``<style/>``, an attribute).
    """

    def __init__(self) -> None:
        super().__init__()
        self.cut = 0
        self._fed = 0
        self._start = 0  # offset of ``rawdata[0]``
        # ``<style`` regions: closed ``(start, end)`` pairs, and the open one.
        self._regions: deque = deque()
        self._open: int | None = None
        self._in_tag = False
        self._unscanned = ""  # text from ``_scan`` on, not yet decided
        self._scan = 0

    def feed(self, data: str) -> None:  # type: ignore[override]
        self._find_style_regions(data)
        self._fed += len(data)
        HTMLParser.feed(self, data.translate(_NO_REFERENCES))
        self._start = self._fed - len(self.rawdata)

    @property
    def held(self) -> int:
        """Length of the unfinished construct the parser is waiting on."""
        return len(self.rawdata)

    def _find_style_regions(self, data: str) -> None:
        """Extend the region scan over ``data``; each step keeps < 7 chars."""
        text, base, pos = self._unscanned + data, self._scan, 0
        while True:
            if self._open is None:
                m = _STYLE_START.search(text, pos)
                if m is None or m.end() == len(text):  # ``\b`` needs a next char
                    keep = m.start() if m else max(pos, len(text) - 5)
                    break
                self._open, self._in_tag, pos = base + m.start(), True, m.end()
            if self._in_tag:
                gt = text.find(">", pos)
                if gt < 0:
                    keep = len(text)
                    break
                self._in_tag, pos = False, gt + 1
            m = _STYLE_END.search(text, pos)
            if m is None:
                keep = max(pos, len(text) - 6)
                break
            self._regions.append((self._open, base + m.start()))
            self._open, pos = None, m.start()
        self._unscanned, self._scan = text[keep:], base + keep

    def _in_style_region(self, offset: int) -> bool:
        # Offsets only grow, so a region that ends before one is done.
        while self._regions and self._regions[0][1] <= offset:
            self._regions.popleft()
        if self._regions and self._regions[0][0] < offset:
            return True
        return self._open is not None and offset > self._open

    def parse_comment(self, i: int, report: bool = True) -> int:
        # Given the whole string, ``<!-->`` ends at the first later ``-->``
        # and is an empty comment only when there is none. Until a ``-->``
        # arrives, the comment is unfinished.
        if commentclose.search(self.rawdata, i + 4) is None:
            return -1
        return super().parse_comment(i, report)

    def updatepos(self, i: int, j: int) -> int:
        # ``goahead`` calls this after each finished construct, with ``j``
        # the end of it in ``rawdata``.
        if (
            j > i
            and len(self.struct.stack) == 1
            and self.cdata_elem is None
            and self.rawdata[j - 1] in _CUT_AFTER
            and not self._in_style_region(self._start + j)
        ):
            self.cut = self._start + j
            self.struct.clear()
        return super().updatepos(i, j)
