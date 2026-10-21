# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Tag render pipeline: ``Tags`` + single/double/style/template variants.

MRO (html elements)::

    div → html_tag → Tags → dom_tag → dom1core → object

``Tags`` owns HTML-oriented serialize (pretty layout, control attrs, Alpine/HTMX
name cleaning). ``dom_tag`` owns the tree model and public ``__render__`` /
``__async_render__`` (per-tree locks). Subclasses only override what must differ.
"""

from __future__ import annotations

import os
import queue
import re
import textwrap
import threading
import typing
from contextvars import ContextVar
from pathlib import Path

from jinja2.utils import htmlsafe_json_dumps
from markupsafe import Markup

from ux_dom.dom.src.dom1core import dom1core
from ux_dom.dom.src.dom_tag import _NAMESPACE_MEMO, dom_tag
from ux_dom.dom.src.utils.dom_util import (
    dom_text,
    escape,
    checked_attr_name,
    checked_tag_name,
    checked_text_state_body,
    escape_attr_minimal,
    InvalidNodeContext,
    safe_attr_value,
    TEXT_STATE_ELEMENTS,
    VERBATIM_ELEMENTS,
)

__all__ = [
    "Tags",
    "SingleTemplates",
    "DoubleTemplates",
    "DoubleTags",
    "SingleTags",
    "StyleTags",
    "PlaceholderTag",
]

_HTML_ATTR_SHORTHAND = {
    "cls": "class",
    "className": "class",
    "classname": "class",
    "classes": "class",
    "class_name": "class",
    "fr": "for",
    "html_for": "for",
    "htmlFor": "for",
}

_SPECIAL_ATTR_PREFIXES = (
    "data_",
    "aria_",
    "x_",
    "v_",
    "ng_",
    "hx_",
    "ws_",
    "sse_",
    "ws__",
    "up_",
    "remove_me",
)

# Serialize hooks the compact token walker re-implements inline. A subclass that
# overrides any of them must be serialized by its own ``_render`` instead.
_WALKER_INLINED_HOOKS = (
    "_render",
    "_render_open_tag",
    "_render_attribute",
    "_render_close_tag",
    "_render_children",
)
_walker_delegates: dict = {}  # type -> bool, filled once per class


def _delegates_to_render(cls) -> bool:
    """True when the compact walker must serialize ``cls`` via ``_render``."""
    cached = _walker_delegates.get(cls)
    if cached is not None:
        return cached
    # ``_walk_covers`` lists overrides the class's own walker already runs.
    covered = getattr(cls, "_walk_covers", ())
    found = any(
        (fn := getattr(cls, h)) is not getattr(Tags, h) and fn not in covered
        for h in _WALKER_INLINED_HOOKS
    )
    _walker_delegates[cls] = found
    return found


# Elements the UA stylesheet lays out as block-level boxes (block, list-item,
# table parts). A newline next to one sits at a line edge, where a browser drops
# it. Everything else is inline: the spec's phrasing content, elements that are
# not displayed, ``legend`` (a fieldset lifts it out of the flow), ``dialog``
# (hidden until open, then positioned out of the flow) and unknown or custom
# elements (the safe default).
_BLOCK_ELEMENTS = frozenset(
    """address article aside blockquote body caption center col colgroup dd
    details dir div dl dt fieldset figcaption figure footer form h1 h2 h3 h4 h5
    h6 header hgroup hr html li listing main menu nav ol p plaintext pre search
    section summary table tbody td tfoot th thead tr ul xmp""".split()
)

# Bodies that render flat by tag name. Whitespace in a raw text or preformatted
# body is content (#88). An ``option`` displays its label, which joins its text
# with one space for each whitespace run, and ``ruby`` lays out everything in it
# inline (#94).
_FLAT_BODIES = VERBATIM_ELEMENTS | {"option", "ruby"}

# How a node sits among its siblings. A wrapper takes its children's max.
_EMPTY, _BLOCK, _INLINE = 0, 1, 2

# The HTML parser closes some elements early when they hold certain descendants
# (``<li><li>``, ``<p><div>``), and what follows lands in the parent. Each such
# descendant is a bit. A node passes up the bits found inside it, minus the ones
# it stops (a ``ul`` ends the search for a nested ``li``).
_ANY_BLOCK, _LI, _DT_DD, _HEADING, _A, _BUTTON, _FORM, _NOBR, _TABLE_PART = (
    1 << n for n in range(9)
)
_ALL_BITS = (1 << 9) - 1
_LIST = (_ANY_BLOCK, _ANY_BLOCK | _LI, 0)
_HEADING_TAG = (_ANY_BLOCK | _HEADING, _ANY_BLOCK, _HEADING)
_PART = _ANY_BLOCK | _TABLE_PART
# name -> (bits it is, bits it stops, bits that close it)
_PARSER_CLOSE = {
    "p": (_ANY_BLOCK, _ANY_BLOCK, _ANY_BLOCK),
    "li": (_ANY_BLOCK | _LI, _ANY_BLOCK, _LI),
    "ul": _LIST,
    "ol": _LIST,
    "menu": _LIST,
    "dt": (_ANY_BLOCK | _DT_DD, _ANY_BLOCK, _DT_DD),
    "dd": (_ANY_BLOCK | _DT_DD, _ANY_BLOCK, _DT_DD),
    "dl": (_ANY_BLOCK, _ANY_BLOCK | _DT_DD, 0),
    "dialog": (_ANY_BLOCK, 0, 0),
    "a": (_A, 0, _A),
    "nobr": (_NOBR, 0, _NOBR),
    "button": (_BUTTON, 0, _BUTTON),
    "form": (_ANY_BLOCK | _FORM, _ANY_BLOCK, _FORM),
    **dict.fromkeys(("h1", "h2", "h3", "h4", "h5", "h6"), _HEADING_TAG),
    # A table part in a cell or caption closes it, unless a nested table holds it.
    "table": (_ANY_BLOCK, _TABLE_PART, 0),
    **dict.fromkeys(("caption", "td", "th"), (_PART, 0, _TABLE_PART)),
    **dict.fromkeys("colgroup col tbody thead tfoot tr".split(), (_PART, 0, 0)),
}
# Elements the parser drops outside their parent (their content stays where it
# is): table parts, and ``html``/``head``/``body`` anywhere but the top of the
# document. Inline content in a table is moved out in front of it.
_PARENTS = {
    "html": (None,),
    "head": (None, "html"),
    "body": (None, "html"),
    "caption": ("table",),
    "colgroup": ("table",),
    "col": ("colgroup", "table"),
    "tbody": ("table",),
    "thead": ("table",),
    "tfoot": ("table",),
    "tr": ("tbody", "thead", "tfoot", "table"),
    "td": ("tr",),
    "th": ("tr",),
}
_TABLE_ROWS = frozenset(("table", "tbody", "thead", "tfoot", "tr"))

# Per-render memo for ``_scan``: id -> (node, result). The node is kept so its
# id cannot be reused by another object while the render runs.
_LAYOUT_MEMO: ContextVar[dict | None] = ContextVar("ux_dom_layout_memo", default=None)


def _scan(node, memo: dict, context: str | None) -> tuple[int, int, bool]:
    """``(layout, closer bits, moved)`` for ``node`` inside a ``context`` tag.

    ``layout`` is ``_EMPTY``, ``_BLOCK`` or ``_INLINE``: text is inline, and a
    wrapper or a Jinja tag with children (``{% if %}``) takes their max.
    ``moved`` means the parser takes the node's tail out of it, so the tail
    lands next to its siblings: it renders flat and counts as inline. A
    ``lazy`` is unknown until it renders, so it counts as inline and as any
    descendant. The walk is post-order on an explicit stack (#125).
    """
    done = _scan_leaf(node, memo)
    if done is not None:
        return done
    # Frame: [node, its HTML name, its context, children left, kind, bits].
    frames = [_scan_frame(node, memo, context)]
    while True:
        frame = frames[-1]
        child = next(frame[3], frames)  # ``frames`` marks the end
        if child is not frames:
            done = _scan_leaf(child, memo)
            if done is None:
                frames.append(_scan_frame(child, memo, frame[1] or frame[2]))
                continue
        else:
            frames.pop()
            done = _scan_close(frame, memo)
            if not frames:
                return done
            frame = frames[-1]
        frame[4], frame[5] = max(frame[4], done[0]), frame[5] | done[1]


def _scan_leaf(node, memo: dict) -> tuple[int, int, bool] | None:
    """``_scan`` of a node with nothing to walk, else ``None``."""
    if isinstance(node, str):
        return (_INLINE if node else _EMPTY), 0, False
    if isinstance(node, dom_text):
        return (_INLINE if node.text else _EMPTY), 0, False
    if not isinstance(node, Tags):
        return _INLINE, _ALL_BITS, False
    hit = memo.get(id(node))
    return None if hit is None else hit[1]


def _scan_frame(node, memo: dict, context: str | None) -> list:
    memo[id(node)] = (node, (_EMPTY, 0, False))  # a cycle holds no more content
    return [node, _html_name(node), context, iter(node.children), 0, 0]


def _scan_close(frame: list, memo: dict) -> tuple[int, int, bool]:
    node, name, context, _, kind, inside = frame
    moved = False
    if name is None and not node.children and node._control(Tags.RENDER_TAG, True):
        kind = _INLINE  # a comment or a Jinja ``{{ var }}``: prints in the line
    elif name is not None:
        own, stops, closers = _PARSER_CLOSE.get(
            name, (_ANY_BLOCK if name in _BLOCK_ELEMENTS else 0, 0, 0)
        )
        moved = (
            bool(inside & closers)
            or (name in _PARENTS and context not in _PARENTS[name])
            or (node.is_single and bool(node.children))  # no end tag holds them
            or (name in _TABLE_ROWS and kind == _INLINE)
        )
        block = name in _BLOCK_ELEMENTS and not moved
        kind, inside = (_BLOCK if block else _INLINE), own | inside & ~stops
    memo[id(node)] = (node, (kind, inside, moved))
    return kind, inside, moved


def _html_name(node) -> str | None:
    """The lower-case tag name when ``node`` renders as an HTML element."""
    if node.left_delimiter != "<" or not node._control(Tags.RENDER_TAG, True):
        return None
    return node._clean_name(node._tagname()).lower()


def _inline_neighbours(node) -> bool:
    """An inline child next to inline content: a sibling, or the inside edge of
    an inline element. A pretty newline there shows as a space."""
    memo = _LAYOUT_MEMO.get()
    if memo is None:
        memo = {}
    name = _html_name(node)
    kind, _, moved = _scan(node, memo, None)
    if moved:
        return True
    if name == "head":
        return False  # nothing in it is displayed
    edge = _INLINE if name is not None and kind == _INLINE else _EMPTY
    prev = edge
    for child in node.children:
        kind = _scan(child, memo, name)[0]
        if kind == _INLINE and prev == _INLINE:
            return True
        prev = kind or prev
    return prev == edge == _INLINE


def _ascii_lower(text):
    # The parser folds ASCII case only. A non-ASCII name matches nothing here.
    text = str(text)
    return text.lower() if text.isascii() else text


def _element_name(node):
    """Lowercase name of the start tag ``node`` writes, or ``None`` if none.

    Tag-less wrappers (``render_tag=False``: Component, PlaceholderTag),
    ``open_tag`` markup and template delimiters write no element.
    """
    if not isinstance(node, Tags) or node.left_delimiter != "<":
        return None
    if not node._control(Tags.RENDER_TAG, True) or node._control(Tags.OPEN_TAG):
        return None
    return _ascii_lower(node._clean_name(node._tagname()))


def _text_state_name(node, name):
    """``node``'s name if the tokenizer reads its body as RCDATA / RAWTEXT.

    ``name`` is the node's cleaned tag name (a cheap filter for the hot path).
    Namespace is not consulted: in ``<svg>`` a breakout tag (``<div>``, ``<p>``)
    pops the parser back to HTML, so an element the tree puts in foreign
    content can still be HTML there (§13.2.6.5).
    """
    name = _ascii_lower(name)
    if name in TEXT_STATE_ELEMENTS and _element_name(node) == name:
        return name
    return None


def _drive(steps):
    """Run render steps (``Tags._render_steps``) on an explicit stack.

    A child that renders like ``Tags`` becomes a frame here instead of a
    nested Python call, so tree depth never reaches the recursion limit
    (#125). A child with its own ``_render`` (a Component, ``lazy``, text) is
    called; only such nodes nest the Python stack, one call each.
    """
    stack = [steps]
    while True:
        try:
            child, args = stack[-1].send(None)
        except StopIteration as done:
            stack.pop()
            if not stack:
                return done.value
            continue
        if type(child)._render is Tags._render:
            stack.append(child._render_steps(*args))
        else:
            child._render(*args[:4], _seen=args[4])


class Tags(dom_tag, dom1core):
    """HTML-oriented tag: control attrs, pretty layout, framework attr names."""

    left_delimiter = "<"
    right_delimiter = ">"
    self_dedent = False
    child_dedent = False
    render_tag = True
    new_line = "\n"
    SELF_DEDENT = "self_dedent"
    CHILD_DEDENT = "child_dedent"
    OPEN_TAG = "open_tag"
    CLOSE_TAG = "close_tag"
    RENDER_TAG = "render_tag"
    CONTROL_ATTRS = frozenset(
        {SELF_DEDENT, CHILD_DEDENT, OPEN_TAG, CLOSE_TAG, RENDER_TAG}
    )
    file_extension = ".html"
    attribute_prefix_map: dict = {}
    # Per-instance map: attribute -> False opts that attribute out of full
    # escaping (it still gets escape_attr_minimal). Never a shared class dict,
    # or one tag's opt-out would disable escaping for every tag.
    safe_attributes: dict

    def __init__(self, *args, **kwargs):
        # Before super().__init__, which may already set attributes.
        self.safe_attributes = {}
        super(Tags, self).__init__(*args, **kwargs)

    def _control(self, key, default=False):
        """Read control flag without permanently popping (idempotent re-render)."""
        if key in self.attributes:
            return self.attributes[key]
        return getattr(self, key, default)

    def _markup_control(self, key):
        """``open_tag`` / ``close_tag``: verbatim markup that replaces the tag.

        They are emitted as-is, so a value must be trusted ``Markup``
        (``__html__``), as the template tags build it. A plain string from
        kwargs, a dict child, or ``tag["open_tag"]`` raises ``TypeError``.
        """
        value = self._control(key, False)
        if not value or callable(getattr(value, "__html__", None)):
            return value
        raise TypeError(
            "%s must be markupsafe.Markup (it is emitted verbatim); got %s"
            % (key, type(value).__name__)
        )

    def _clean_name(self, name):
        if any(name):
            if name[-1] == "_":
                name = name[:-1]
            if name[0] == "_":
                name = name[1:]
        return name

    @classmethod
    def clean_attribute(cls, attribute):
        """Normalize attribute names (shorthand + Alpine/Vue/HTMX/Angular)."""
        attribute = _HTML_ATTR_SHORTHAND.get(attribute, attribute)

        if (
            isinstance(attribute, str)
            and attribute.startswith("__")
            and attribute.endswith("__")
            and len(attribute) >= 4
        ):
            return attribute

        if len(attribute) >= 2:
            if attribute[0] == "_" and attribute[1] != "_":
                attribute = attribute[1:]
            if attribute[-1] == "_" and attribute[:-1].isidentifier():
                attribute = attribute[:-1]

        if (
            attribute.startswith("__")
            and len(attribute) > 2
            and not attribute.endswith("__")
        ):
            return ":" + attribute[2:].replace("_", "-")

        special_prefix = attribute.startswith(_SPECIAL_ATTR_PREFIXES) or any(
            attribute.startswith(x) for x in cls.attribute_prefix_map
        )
        if attribute in {"http_equiv"} or special_prefix:
            attribute = attribute.replace("_", "-")
            attribute = attribute.replace("--", ":")
            attribute = attribute.replace("v-bind-", ":")
            attribute = attribute.replace("v-bind", "")
            attribute = attribute.replace("x-bind-", ":")
            attribute = attribute.replace("x-bind", "")
            attribute = attribute.replace("transition-enter", "transition:enter")
            attribute = attribute.replace("transition-leave", "transition:leave")
            attribute = attribute.replace("intersect-enter", "intersect:enter")
            attribute = attribute.replace("intersect-leave", "intersect:leave")
            if attribute.startswith("v-on:"):
                attribute = "@" + attribute[len("v-on:") :]
            elif attribute.startswith("v-on-"):
                attribute = "@" + attribute[len("v-on-") :]
            elif attribute.startswith("x-on:"):
                attribute = "@" + attribute[len("x-on:") :]
            elif attribute.startswith("x-on-"):
                attribute = "@" + attribute[len("x-on-") :]
            attribute = attribute.replace("-dot-", ".")
            if attribute.startswith("hx-on-") and not attribute.startswith("hx-on:"):
                attribute = "hx-on:" + attribute[len("hx-on-") :]
            if attribute in cls.attribute_prefix_map:
                attribute = cls.attribute_prefix_map[attribute]

        if attribute.split("_")[0] in ("xlink", "xml", "xmlns"):
            attribute = attribute.replace("_", ":", 1)

        return attribute

    def _wrap_attr_value(self, value, indent_level, indent_str, pretty):
        value = textwrap.dedent(value)
        return re.sub(r"\s+", " ", value.strip())

    def _iter_html_attrs(self, indent_level=None, indent_str=None, pretty=None):
        """Yield HTML attribute fragments (list-render and token-walk share this)."""
        name = self._clean_name(self._tagname())
        for attribute, value in sorted(self.attributes.items()):
            if attribute in getattr(self, "CONTROL_ATTRS", ()):
                continue
            if value is False:
                continue
            attribute = checked_attr_name(attribute)
            if value is True and attribute.lower() in self.boolean_attributes:
                value = attribute
            if value is None:
                yield " %s" % attribute
                continue
            if attribute == "class":
                value = self._wrap_attr_value(
                    value, indent_level, indent_str, pretty
                )
            if not isinstance(value, (dict, list)):
                value = safe_attr_value(attribute, value, name)
                if self.safe_attributes.get(attribute, True):
                    yield ' %s="%s"' % (attribute, escape(str(value), True))
                else:
                    yield ' %s="%s"' % (attribute, escape_attr_minimal(value))
            else:
                # The JSON text is what the browser reads (SMIL splits it on
                # ``;``), so the URL check runs on it, not on the object (#86).
                dumped = safe_attr_value(attribute, htmlsafe_json_dumps(value), name)
                yield " %s='%s'" % (
                    attribute,
                    escape(str(dumped), quote=False),
                )

    def _render_attribute(self, sb, indent_level, indent_str, pretty):
        for tok in self._iter_html_attrs(indent_level, indent_str, pretty):
            sb.append(tok)
        return sb

    def _render_open_tag(
        self,
        /,
        sb,
        name,
        open_tag,
        indent_level=None,
        indent_str=None,
        pretty=None,
    ):
        if open_tag:
            sb.append("%s" % open_tag)
        else:
            sb.append(self.left_delimiter)
            sb.append(checked_tag_name(name))
            self._render_attribute(sb, indent_level, indent_str, pretty)
            sb.append(self.right_delimiter)
        return sb

    def _render_close_tag(self, /, sb, name, close_tag):
        if close_tag:
            sb.append("%s" % close_tag)
        else:
            sb.append("".join([self.left_delimiter, "/"]))
            sb.append(checked_tag_name(name))
            sb.append(self.right_delimiter)
        return sb

    def _new_line_and_inline_handler(
        self, sb, indent_level, indent_str, pretty, is_inline
    ):
        if pretty and not is_inline:
            is_inline = False
            sb.append(self.new_line)
            sb.append(indent_str * indent_level)
        return sb, is_inline

    @staticmethod
    def _dedent_handler(dedent, indent_level):
        if dedent:
            indent_level -= 1
        return indent_level

    def _render_children(self, sb, indent_level, indent_str, pretty, _seen=None):
        """Render children with partial-inline + self_dedent.

        Indent contract: never dedent a child past parent-1; newlines before a
        child use ``(inline and self.is_inline)`` so non-inline parents still
        break before inline children.
        """
        return _drive(
            self._render_children_steps(sb, indent_level, indent_str, pretty, _seen)
        )

    def _render_children_steps(self, sb, indent_level, indent_str, pretty, _seen):
        """``_render_children`` as steps for ``_drive``: each child render is
        yielded as ``(child, args)`` instead of called."""
        inline = True
        orig_indent = indent_level
        self_render_tag = self._control(Tags.RENDER_TAG, True)

        for child in self.children:
            if isinstance(child, dom_tag) and not isinstance(child, dom_text):
                child_self_dedent = (
                    child._control(Tags.SELF_DEDENT, False)
                    if hasattr(child, "_control")
                    else getattr(child, Tags.SELF_DEDENT, False)
                )

                if pretty and not child.is_inline:
                    inline = False
                    if child_self_dedent and not self.is_single:
                        if indent_level > orig_indent - 1:
                            indent_level = self._dedent_handler(True, indent_level)

                if self_render_tag:
                    if not isinstance(child, PlaceholderTag) or (
                        isinstance(child, PlaceholderTag) and any(child)  # type: ignore[arg-type]
                    ):
                        sb, inline = self._new_line_and_inline_handler(
                            sb,
                            indent_level,
                            indent_str,
                            pretty,
                            inline and self.is_inline,
                        )

                yield child, (sb, indent_level, indent_str, pretty, _seen)

            else:
                if isinstance(child, dom_text):
                    # The render holds the tree lock already; ``__render__``
                    # would walk to the root again for every text (#125).
                    child = "".join(child._render([]))

                if child or any(child):
                    if pretty:
                        inline = False
                        if self_render_tag:
                            sb, inline = self._new_line_and_inline_handler(
                                sb,
                                indent_level,
                                indent_str,
                                pretty,
                                inline and self.is_inline,
                            )
                        lines = child.splitlines()
                        for line in lines:
                            sb.append(str(line))
                            if line and line != lines[-1]:
                                sb, inline = self._new_line_and_inline_handler(
                                    sb,
                                    indent_level,
                                    indent_str,
                                    pretty,
                                    inline and self.is_inline,
                                )
                    else:
                        sb.append(str(child))

            if child or any(child):
                if not isinstance(child, PlaceholderTag) or (
                    isinstance(child, PlaceholderTag) and any(child)  # type: ignore[arg-type]
                ):
                    if (
                        not self_render_tag
                        and pretty
                        and self.children
                        and self.children[-1] != child
                    ):
                        sb, inline = self._new_line_and_inline_handler(
                            sb,
                            indent_level,
                            indent_str,
                            pretty,
                            inline and self.is_inline,
                        )

        return inline

    def _render(self, sb, indent_level=1, indent_str="  ", pretty=True, _seen=None):
        if _NAMESPACE_MEMO.get() is None:
            # One namespace memo per render pass (``_parsed_namespace``).
            token = _NAMESPACE_MEMO.set({})
            try:
                return Tags._render(
                    self, sb, indent_level, indent_str, pretty, _seen=_seen
                )
            finally:
                _NAMESPACE_MEMO.reset(token)
        if pretty and _LAYOUT_MEMO.get() is None:
            # One memo per pretty render keeps the layout check linear.
            token = _LAYOUT_MEMO.set({})
            try:
                return Tags._render(
                    self, sb, indent_level, indent_str, pretty, _seen=_seen
                )
            finally:
                _LAYOUT_MEMO.reset(token)
        return _drive(self._render_steps(sb, indent_level, indent_str, pretty, _seen))

    def _render_steps(self, sb, indent_level, indent_str, pretty, _seen):
        """``_render`` as steps for ``_drive`` (the memos are already set)."""
        if _seen is None:
            _seen = set()
        sid = id(self)
        if sid in _seen:
            sb.append("<!--cycle:%s-->" % type(self).__name__)
            return sb
        _seen.add(sid)

        self.open_tag = self._markup_control(Tags.OPEN_TAG)
        self.close_tag = self._markup_control(Tags.CLOSE_TAG)
        pretty = pretty and self.is_pretty and not self.is_inline
        pretty = pretty and _element_name(self) not in _FLAT_BODIES
        # Inline neighbours render flat: ``<b>a</b><i>b</i>`` must not show as
        # ``a b``, nor ``a&#39;b`` as ``a ' b``.
        pretty = pretty and not _inline_neighbours(self)

        self_dedent = self._control(Tags.SELF_DEDENT, False)
        self.self_dedent = self_dedent
        self_child_dedent = self._control(Tags.CHILD_DEDENT, False)
        self.child_dedent = self_child_dedent
        self_render_tag = self._control(Tags.RENDER_TAG, True)

        dedent = not self_render_tag
        if pretty and dedent:
            indent_level = self._dedent_handler(dedent, indent_level)

        if self_render_tag:
            name = self._clean_name(self._tagname())
            self._render_open_tag(
                sb=sb,
                name=name,
                open_tag=self.open_tag,
                indent_level=indent_level,
                indent_str=indent_str,
                pretty=pretty,
            )

        # RCDATA / RAWTEXT (#90): check the joined body, as #53 does.
        text_state = _text_state_name(self, name) if self_render_tag else None
        body = [] if text_state else sb
        args = (
            body,
            (
                indent_level + 1
                if not self.is_single or not self_child_dedent
                else indent_level
            ),
            indent_str,
            pretty,
            _seen,
        )
        if type(self)._render_children is Tags._render_children:
            inline = yield from self._render_children_steps(*args)
        else:
            inline = self._render_children(*args)
        if text_state:
            sb.append(checked_text_state_body("".join(map(str, body)), text_state))
        inline = self.is_inline and inline
        if self_render_tag and not self.is_single:
            sb, inline = self._new_line_and_inline_handler(
                sb, indent_level, indent_str, pretty, inline
            )
            name = self._clean_name(self._tagname())
            self._render_close_tag(sb=sb, name=name, close_tag=self.close_tag)

        return sb

    def _iter_pretty_stream(
        self,
        indent_level,
        indent_str,
        pretty,
        _seen=None,
        *,
        maxsize=256,
        stream_mode=None,
        put_timeout=30.0,
        get_timeout=30.0,
    ):
        """Pretty tokens: ``safe`` (default) or ``worker`` queue."""
        mode = (stream_mode or os.environ.get("UI_DOM_PRETTY_STREAM") or "safe").lower()
        if mode in ("safe", "buffer", "same_thread", "sync"):
            sb: list = []
            self._render(sb, indent_level, indent_str, pretty, _seen=_seen)
            yield from sb
            return
        if mode not in ("worker", "thread", "queue"):
            raise ValueError(
                f"unknown pretty stream_mode={mode!r}; use 'safe' or 'worker'"
            )
        yield from self._iter_pretty_stream_worker(
            indent_level,
            indent_str,
            pretty,
            _seen=_seen,
            maxsize=maxsize,
            put_timeout=put_timeout,
            get_timeout=get_timeout,
        )

    def _iter_pretty_stream_worker(
        self,
        indent_level,
        indent_str,
        pretty,
        _seen=None,
        *,
        maxsize=256,
        put_timeout=30.0,
        get_timeout=30.0,
    ):
        q: "queue.Queue" = queue.Queue(maxsize=max(8, int(maxsize)))
        sentinel = object()
        error: list = []
        abandoned = threading.Event()

        class _QueueSb:
            __slots__ = ()

            def append(self, item):
                if abandoned.is_set():
                    raise RuntimeError("pretty stream consumer abandoned")
                try:
                    q.put(item, timeout=put_timeout)
                except queue.Full as exc:
                    raise TimeoutError(
                        "pretty stream queue full / consumer too slow "
                        f"(maxsize={maxsize}, put_timeout={put_timeout})"
                    ) from exc

        def worker():
            try:
                from ux_dom.dom.src.concurrency import multi_tree_lock

                with multi_tree_lock(self):
                    self._render(
                        _QueueSb(),
                        indent_level,
                        indent_str,
                        pretty,
                        _seen=_seen,
                    )
            except Exception as exc:  # noqa: BLE001
                error.append(exc)
            finally:
                try:
                    q.put(sentinel, timeout=put_timeout)
                except Exception:
                    pass

        th = threading.Thread(
            target=worker, name="ux_dom-pretty-stream", daemon=True
        )
        th.start()
        try:
            while True:
                try:
                    item = q.get(timeout=get_timeout)
                except queue.Empty as exc:
                    abandoned.set()
                    raise TimeoutError(
                        "pretty stream stalled (worker hung or deadlocked) "
                        f"get_timeout={get_timeout}"
                    ) from exc
                if item is sentinel:
                    break
                yield item
        except GeneratorExit:
            abandoned.set()
            raise
        finally:
            abandoned.set()
            th.join(timeout=min(5.0, float(get_timeout)))
        if error:
            raise error[0]

    def _walk_render_tokens(self, indent_level, indent_str, pretty, _seen=None):
        """Token generator for async/stream serialize (compact or pretty).

        Iterative, like ``_drive``: a child that walks like ``Tags`` is a
        frame on an explicit stack, not a nested generator (#125).
        """
        pretty_flag = bool(pretty and self.is_pretty and not self.is_inline)
        if pretty_flag:
            yield from self._iter_pretty_stream(
                indent_level, indent_str, pretty, _seen=_seen
            )
            return
        if _seen is None:
            _seen = set()
        stack = [self._walk_steps(indent_level, indent_str, pretty, _seen)]
        while stack:
            item = next(stack[-1], None)
            if item is None:
                stack.pop()
            elif isinstance(item, str):
                yield item
            elif type(item[0])._walk_render_tokens is Tags._walk_render_tokens:
                # Children inherit the parent's effective (compact) layout,
                # as in _render.
                stack.append(item[0]._walk_steps(item[1], indent_str, False, _seen))
            else:
                yield from item[0]._walk_render_tokens(
                    item[1], indent_str, False, _seen=_seen
                )

    def _walk_steps(self, indent_level, indent_str, pretty, _seen):
        """One node's compact tokens; a child tag is yielded as
        ``(child, indent_level)`` for ``_walk_render_tokens`` to expand."""
        # Overridden hooks (StyleTags dialects, ReactiveComponent's pre-serialize
        # refresh) only run inside ``_render``.
        cls = type(self)
        delegate = _walker_delegates.get(cls)
        if delegate is None:
            delegate = _delegates_to_render(cls)
        if delegate:
            yield from self._render([], indent_level, indent_str, pretty, _seen=_seen)
            return

        sid = id(self)
        if sid in _seen:
            yield "<!--cycle:%s-->" % type(self).__name__
            return
        _seen.add(sid)

        open_tag = self._markup_control(Tags.OPEN_TAG)
        close_tag = self._markup_control(Tags.CLOSE_TAG)
        self_render_tag = self._control(Tags.RENDER_TAG, True)
        self.open_tag = open_tag
        self.close_tag = close_tag

        if self_render_tag:
            name = self._clean_name(self._tagname())
            if _text_state_name(self, name):  # its body is checked as a whole
                _seen.discard(sid)
                yield from self._render(
                    [], indent_level, indent_str, pretty, _seen=_seen
                )
                return
            if open_tag:
                yield str(open_tag)
            else:
                yield self.left_delimiter
                yield checked_tag_name(name)
                yield from self._iter_html_attrs(indent_level, indent_str, pretty)
                yield self.right_delimiter

        for child in self.children:
            if isinstance(child, dom_tag):
                yield child, indent_level + 1
            else:
                if child or any(str(child)):
                    yield str(child)

        if self_render_tag and not self.is_single:
            name = self._clean_name(self._tagname())
            if close_tag:
                yield str(close_tag)
            else:
                yield self.left_delimiter
                yield "/"
                yield checked_tag_name(name)
                yield self.right_delimiter

    def __and__(self, other: dom_tag) -> "Tags":
        return (
            PlaceholderTag(__inline=self.is_inline, __pretty=self.is_pretty)
            & self
            & other
        )

    def __iter__(self) -> typing.List[typing.Union[str, dom_tag, "Tags"]]:
        return super().__iter__()

    def save(
        self,
        file_name: typing.Union[str, Path, None] = None,
        folder_name: typing.Union[str, Path, None] = None,
        current_dir: bool = False,
        file_or_dir: typing.Union[str, Path, None] = None,
    ):
        if file_or_dir is not None:
            assert (
                folder_name is None and current_dir is False
            ), "folder_name and current_dir can't be initialised with file_path"
            file_or_dir = Path(file_or_dir)
        else:
            folder_name = Path(folder_name or Path(__file__).parent / "static")
            assert folder_name is not None, "folder_name should be initialised"

        if self.file_extension is None:
            raise ValueError(
                f"can not save file with {self.file_extension=} type extension"
            )

        def _filename() -> Path:
            nonlocal file_name
            file_name = Path(file_name or str(self.__class__.__name__))
            if file_name.suffix:
                if not file_name.suffix == self.file_extension:
                    raise ValueError(
                        f"{file_name.suffix=} and {self.file_extension=} did not match"
                    )
            else:
                file_name = file_name.with_suffix(self.file_extension)
            return file_name

        if folder_name is not None:
            current_work_dir = Path.cwd()
            dir_name = current_work_dir if current_dir else current_work_dir.parent
            dir_folder = dir_name / folder_name
            if not dir_folder.exists():
                dir_folder.mkdir()
            file_path = dir_folder / _filename()
        elif file_or_dir is not None:
            file_path = (
                file_or_dir / _filename() if file_or_dir.is_dir() else file_or_dir
            )

        html_string = self.__render__()
        if not file_path.exists():
            with file_path.open(mode="w+") as f:
                f.write(html_string)
        else:
            with file_path.open(mode="r") as temp:
                old_html = temp.read()
                if old_html != html_string:
                    with file_path.open(mode="w") as f:
                        f.write(html_string)
        return file_path.name


class PlaceholderTag(Tags):
    render_tag = False

    def __and__(self, other: dom_tag) -> Tags:
        return PlaceholderTag(
            self, other, __inline=self.is_inline, __pretty=self.is_pretty
        )


class SingleTags(Tags):
    left_delimiter = "<"
    right_delimiter = ">"
    is_single = True


class DoubleTags(Tags):
    left_delimiter = "<"
    right_delimiter = ">"


class SingleTemplates(SingleTags):
    boolean_attributes = frozenset()  # template tags, not HTML elements
    left_delimiter = "{%"
    right_delimiter = "%}"
    self_dedent = False
    child_dedent = False
    enable_left_delimiter_space = True
    enable_right_delimiter_space = True
    enable_space_in_between = True

    def __init__(
        self,
        template_name,
        template_text,
        *dom_elements,
        self_dedent=None,
        child_dedent=None,
        **kwargs,
    ):
        open_tag = (
            "".join(
                [
                    self.left_delimiter,
                    " " if self.enable_left_delimiter_space else "",
                    template_name,
                    " " if self.enable_space_in_between else "",
                    template_text,
                    " " if self.enable_right_delimiter_space else "",
                    self.right_delimiter,
                ]
            )
            if any(template_name)
            else (
                "".join(
                    [
                        self.left_delimiter,
                        " " if self.enable_left_delimiter_space else "",
                        template_text,
                        " " if self.enable_right_delimiter_space else "",
                        self.right_delimiter,
                    ]
                )
            )
        )
        super(SingleTemplates, self).__init__(
            open_tag=Markup(open_tag),
            self_dedent=self_dedent or self.self_dedent,
            child_dedent=child_dedent or self.child_dedent,
            **kwargs,
        )
        if any(dom_elements):
            self._add(*dom_elements)


class DoubleTemplates(DoubleTags):
    boolean_attributes = frozenset()  # template tags, not HTML elements
    left_delimiter = "{%"
    right_delimiter = "%}"
    self_dedent = True
    child_dedent = True
    closing_template_tag = "end"
    enable_left_delimiter_space = True
    enable_right_delimiter_space = True
    enable_space_in_between = True

    def __init__(
        self,
        template_name,
        template_text,
        *dom_elements,
        self_dedent=None,
        child_dedent=None,
        **kwargs,
    ):
        open_tag = "".join(
            [
                self.left_delimiter,
                " " if self.enable_left_delimiter_space else "",
                template_name,
                " " if self.enable_space_in_between else "",
                template_text,
                " " if self.enable_right_delimiter_space else "",
                self.right_delimiter,
            ]
        )
        close_tag = "".join([self.closing_template_tag, template_name])
        close_tag = "".join(
            [
                self.left_delimiter,
                " " if self.enable_left_delimiter_space else "",
                close_tag,
                " " if self.enable_right_delimiter_space else "",
                self.right_delimiter,
            ]
        )
        super(DoubleTemplates, self).__init__(
            open_tag=Markup(open_tag),
            close_tag=Markup(close_tag),
            self_dedent=self_dedent or self.self_dedent,
            child_dedent=child_dedent or self.child_dedent,
            **kwargs,
        )
        if any(dom_elements):
            self._add(*dom_elements)


class StyleTags(Tags):
    left_delimiter = "{"
    right_delimiter = "}"
    self_dedent = False
    tagname_prefix = ""
    attribute_joiner = "%s: %s;"

    def _render(self, sb, *args, **kwargs):
        """A CSS rule renders inside ``<style>`` or standalone, never as HTML.

        Its selector and rule text are emitted raw. ``<style>`` neutralizes
        ``</style`` over its joined body; as the child of any other element the
        text would land in HTML context (#81), so that raises
        ``InvalidNodeContext``. Other CSS rules and tag-less wrappers
        (``rule & rule``) pass the context through.
        """
        node, seen = self.parent, {id(self)}
        while node is not None and getattr(type(node), "raw_text", None) != "style":
            transparent = isinstance(node, StyleTags) or (
                isinstance(node, Tags) and not node._control(Tags.RENDER_TAG, True)
            )
            if not transparent:
                raise InvalidNodeContext(
                    "%s is a CSS rule; render it inside <style>, not <%s>"
                    % (type(self).__name__, node._tagname())
                )
            if id(node) in seen:  # parent cycle: no HTML ancestor
                break
            seen.add(id(node))
            node = node.parent
        return super()._render(sb, *args, **kwargs)

    def _render_open_tag(
        self,
        /,
        sb,
        name,
        open_tag,
        indent_level=None,
        indent_str=None,
        pretty=None,
    ):
        sb.append(name)
        if pretty:
            sb.append(" ")
        sb.append(self.left_delimiter)
        if pretty:
            sb.append("\n")
            sb.append(indent_str * indent_level)
        sb = self._render_attribute(
            sb=sb,
            indent_level=indent_level,
            indent_str=indent_str,
            pretty=pretty,
        )
        return sb

    def _render_attribute(self, /, sb, indent_level, indent_str, pretty):
        attribute_joiner = (
            f"{self.attribute_joiner}".replace(" ", "")
            if not pretty
            else f"{indent_str}{self.attribute_joiner}\n" + (indent_str * indent_level)
        )

        attribute_items = self.attributes.items()

        for attribute, value in attribute_items:
            if value is not False:
                attribute = checked_attr_name(attribute)
            if (
                value is not False and value is not None
            ):  # False values must be omitted completely
                safe = escape(str(safe_attr_value(attribute, value)), True)
                sb.append(attribute_joiner % (attribute, safe))

            if value is None:  # a bare (minimized) attribute
                sb.append(" %s" % attribute)
        return sb

    def _render_close_tag(self, /, sb, name, close_tag):
        sb.append(self.right_delimiter)
        return sb

    def _clean_name(self, name):
        # Workaround for python keywords and standard classes/methods
        # (del, object, input)
        if any(name):  # to handle the case when tagname = ""
            if name[-1] == "_":
                name = name[:-1]
            if name[0] == "_":
                name = name[1:]

        name = "".join([self.tagname_prefix, name])

        return name

    @property
    def attr(self):
        r = []
        attribute_joiner = self.attribute_joiner

        for attribute, value in self.attributes.items():
            if value is not False:
                attribute = checked_attr_name(attribute)
            if (
                value is not False and value is not None
            ):  # False values must be omitted completely
                safe = escape(str(safe_attr_value(attribute, value)), True)
                r.append(attribute_joiner % (attribute, safe))

            if value is None:  # a bare (minimized) attribute
                r.append(" %s" % attribute)
        return " ".join(r)

    @classmethod
    def clean_attribute(cls, attribute):
        """
        Normalize attribute names for shorthand and work around for limitations
        in Python's syntax.
        """

        # Shorthand
        attribute = {
            "cls": "class",
            "className": "class",
            "class_name": "class",
            "fr": "for",
            "html_for": "for",
            "htmlFor": "for",
        }.get(attribute, attribute)

        # Workaround for Python's reserved words
        if attribute[0] == "_":
            attribute = attribute[1:]

        attribute = attribute.replace("_", "-")

        # Workaround for colon
        if attribute.split("_")[0] in ("xlink", "xml", "xmlns"):
            attribute = attribute.replace("_", ":", 1)

        return attribute
