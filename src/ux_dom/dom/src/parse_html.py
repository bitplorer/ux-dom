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

Note: optional tags are not accounted for
(see https://html.spec.whatwg.org/multipage/syntax.html#optional-tags)

"""

from __future__ import annotations

import inspect
import itertools
import re
from collections import abc, deque
from html import escape
from html.parser import HTMLParser
from html.parser import commentclose  # type: ignore[attr-defined]
from typing import Any, Callable, Iterable, Iterator


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
        return (
            f"<{self.name}{' ' if self.attrs else ''}{self.attrs}>"
            + "".join(
                child.render(tag_overrides=tag_overrides, **kwargs) for child in self
            )
            + f"</{self.name}>"
        )


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


class Tree:
    """The engine class to generate the AST tree."""

    def __init__(self, name: str = ""):
        """Initialise Tree"""
        self.name = name
        self.outmost = Root(name)
        self.stack: deque = deque()
        self.stack.append(self.outmost)

    def clear(self):
        """Clear the outmost and stack for a new parsing."""
        self.outmost = Root(self.name)
        self.stack.clear()
        self.stack.append(self.outmost)

    def last(self) -> Element:
        """Return the last pointer which point to the actual tag scope."""
        return self.stack[-1]

    def nest_tag(self, name: str, attrs):
        """Nest a given tag at the bottom of the tree using
        the last stack's pointer.
        """
        pointer = self.stack.pop()
        item = Tag(name, _normalize_attrs(attrs))
        pointer.append(item)
        self.stack.append(pointer)
        self.stack.append(item)

    def nest_xtag(self, name: str, attrs):
        """Nest an XTag onto the tree."""
        top = self.last()
        item = XTag(name, _normalize_attrs(attrs))
        top.append(item)

    def nest_vtag(self, name: str, attrs):
        """Nest a VoidTag onto the tree."""
        top = self.last()
        item = VoidTag(name, _normalize_attrs(attrs))
        top.append(item)

    def nest_terminal(self, klass: type[TerminalElement], data: str):
        """Nest the data onto the tree."""
        top = self.last()
        item = klass(data)
        top.append(item)

    def enclose(self, name: str):
        """When a closing tag is found, pop the pointer's scope from the stack,
        to then point to the earlier scope's tag.
        """
        count = 0
        for ind in reversed(self.stack):
            count = count + 1
            if ind.name == name:
                break
        else:
            count = 0

        # It pops all the items which do not match with the closing tag.
        for _ in range(0, count):
            self.stack.pop()


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
        if tag in self.void_elements:
            self.struct.nest_vtag(tag, attrs)
        else:
            self.struct.nest_tag(tag, attrs)

    def handle_startendtag(self, tag: str, attrs):  # type: ignore[override]
        """When found a XHTML tag style then nest it up to the tree."""
        self.struct.nest_xtag(tag, attrs)

    def handle_endtag(self, tag: str):  # type: ignore[override]
        """When found a closing tag then makes it point to the right scope."""
        if tag not in self.void_elements:
            self.struct.enclose(tag)

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
