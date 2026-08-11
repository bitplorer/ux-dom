# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""In-memory DOM node model: children, attributes, membership, serialize.

Surfaces as tag instances (div(...)) and __render__ / __async_render__.

Design: ContextVar parent stack for concurrent with-builders; per-root locks
from concurrency wrap mutate + serialize; membership is ownership-aware
(docs/internals/MEMBERSHIP.md). Private helpers are _prefixed.
"""
import copy

# pylint: disable=bad-indentation, bad-whitespace, missing-docstring
import numbers
import threading
import typing

from ux_dom.dom.src.concurrency import multi_tree_lock, tree_lock_for
from collections import defaultdict, namedtuple
from functools import wraps

try:
    # Python 3
    from collections.abc import Callable
except ImportError:
    # Python 2.7
    from collections import Callable  # type: ignore

try:
    basestring = basestring  # type: ignore
except NameError:  # py3
    basestring = str
    unicode = str

try:
    import greenlet  # type: ignore
except ImportError:
    greenlet = None

try:
    import contextvars
    from contextvars import ContextVar
except ImportError:  # pragma: no cover
    contextvars = None  # type: ignore
    ContextVar = None  # type: ignore

__all__ = ["dom_string", "dom_tag", "get_current", "attr", "context_stack", "tree_lock_for", "multi_tree_lock"]


# Context stacks: ONE mechanism (ContextVar) for sync and async.
# Pipeline: sync with → __render__; async with → __async_render__.
# Build stack + request vars (CSP) both use ContextVar on the active Context/Task.

if ContextVar is not None:
    _WITH_STACK = ContextVar("ux_dom_dom_with_stack", default=None)
else:  # pragma: no cover
    _WITH_STACK = None  # type: ignore


def _peek_with_stack():
    """Return the active stack list, or None if no with-frame is open.

    Does **not** create a stack (creating an empty list would be copied by
    reference into child asyncio Tasks and shared — classic ContextVar pitfall).
    """
    if _WITH_STACK is None:  # pragma: no cover
        return getattr(dom_tag, "_render_stack", None)
    return _WITH_STACK.get()


def _get_with_stack():
    """Stack for the current Context; create a **new** list only when needed.

    If the current value is None **or** an empty list left over from a parent
    Context copy, allocate a fresh list so concurrent Tasks never share frames.
    """
    if _WITH_STACK is None:  # pragma: no cover
        if not hasattr(dom_tag, "_render_stack"):
            dom_tag._render_stack = []  # type: ignore
        return dom_tag._render_stack  # type: ignore
    stack = _WITH_STACK.get()
    if not stack:  # None or []
        stack = []
        _WITH_STACK.set(stack)
    return stack


def _clear_with_stack_if_empty():
    if _WITH_STACK is None:
        return
    stack = _WITH_STACK.get()
    if stack is not None and len(stack) == 0:
        _WITH_STACK.set(None)


def _get_thread_context():
    """Debug fingerprint (thread, task, greenlet). Prefer ContextVar for storage."""
    parts = [threading.get_ident()]
    try:
        import asyncio

        task = asyncio.current_task()
        parts.append(id(task) if task is not None else 0)
    except RuntimeError:
        parts.append(0)
    if greenlet is not None:
        parts.append(id(greenlet.getcurrent()))
    return tuple(parts)


def context_stack():
    """Copy of active build frames (empty if no with/async with)."""
    if _WITH_STACK is None:
        return []
    stack = _WITH_STACK.get()
    return list(stack) if stack else []


class dom_string(basestring):
    pass


class dom_tag(object):
    is_single = False  # Tag does not require matching end tag (ex. <hr/>)
    is_pretty = True  # Text inside the tag should be left as-is (ex. <pre>)
    # otherwise, text will be escaped() and whitespace may be
    # modified
    is_inline = False
    escape_string = True

    def __new__(_cls, *args, **kwargs):
        """
        Check if bare tag is being used as a decorator
        (called with a single function arg).
        decorate the function and return
        """
        if (
            len(args) == 1
            and isinstance(args[0], Callable)
            and not isinstance(args[0], dom_tag)
            and not kwargs
        ):
            wrapped = args[0]

            @wraps(wrapped)
            def f(*args, **kwargs):
                with _cls() as _tag:
                    return wrapped(*args, **kwargs) or _tag

            return f
        return object.__new__(_cls)

    def __init__(self, *args, **kwargs):
        """
        Creates a new tag. Child tags should be passed as arguments and attributes
        should be passed as keyword arguments.

        There is a non-rendering attribute which controls how the tag renders:

        * `__inline` - Boolean value. If True renders all children tags on the same
                       line.
        """

        self.attributes = {}
        # Tree model is list-backed (mutable DOM). Serialize streams *tokens*
        # lazily; membership must not re-materialize full match lists — see
        # ``_find`` / ``__contains__``.
        self.children: typing.List[typing.Union[str, dom_tag]] = []
        self.parent = None
        self.document = None

        # Does not insert newlines on all children if True (recursive attribute)
        self.is_inline = kwargs.pop("__inline", self.is_inline)
        self.is_pretty = kwargs.pop("__pretty", self.is_pretty)
        self.escape_string = kwargs.pop("__escape_string", self.escape_string)

        # Add child elements
        if args:
            self.add(*args)

        for attr, value in kwargs.items():
            self.set_attribute(*type(self).clean_pair(attr, value))

        # this is where the this class instance is added to the parent context via _add_to_context
        self._ctx: typing.Optional[dom_tag.frame] = None
        self._add_to_ctx()

    # context manager frames live in ContextVar ``_WITH_STACK`` (sync + async).
    frame = namedtuple("frame", ["tag", "items", "used"])
    # ContextVar owns the open-tag stack; this map is unused.
    _with_contexts: typing.DefaultDict = defaultdict(list)

    def _add_to_ctx(self):
        """Attach this node to the innermost active with / async with frame."""
        stack = _peek_with_stack()
        if stack:
            self._ctx = stack[-1]
            stack[-1].items.append(self)

    def __enter__(self):
        """Push construction frame (sync ``with``) — ContextVar stack.

        Build phase only. Pair with ``__render__`` for sync serialize.
        """
        stack = _get_with_stack()
        stack.append(dom_tag.frame(self, [], set()))
        return self

    def __exit__(self, type, value, traceback):
        """Pop construction frame and adopt unused children."""
        stack = _get_with_stack()
        if not stack:
            return None
        frame = stack.pop()
        for item in frame.items:
            if item in frame.used:
                continue
            self.add(item)
        _clear_with_stack_if_empty()
        return None

    async def __aenter__(self):
        """Push construction frame (async ``async with``) — same ContextVar.

        asyncio gives each Task its own Context, so concurrent builders isolate.
        Build only — pair with ``__async_render__`` after the tree exists.
        """
        import asyncio

        await asyncio.sleep(0)
        return self.__enter__()

    async def __aexit__(self, type, value, traceback):
        """Pop construction frame (async ``async with``)."""
        import asyncio

        result = self.__exit__(type, value, traceback)
        await asyncio.sleep(0)
        return result

    def __call__(self, func):
        """
        tag instance is being used as a decorator.
        wrap func to make a copy of this tag
        """
        # remove decorator from its context so it doesn't
        # get added in where it was defined
        if self._ctx:
            self._ctx.used.add(self)

        @wraps(func)
        def f(*args, **kwargs):
            tag = copy.deepcopy(self)
            tag._add_to_ctx()
            with tag:
                return func(*args, **kwargs) or tag

        return f

    def set_attribute(self, key, value):
        """
        Add or update the value of an attribute, or replace a child by index.

        Thread-safe: holds the tree root lock (and the previous parent's lock
        when re-parenting a node by index).
        """
        extra = []
        if isinstance(key, int) and isinstance(value, dom_tag):
            prev = getattr(value, "parent", None)
            if prev is not None and prev is not self:
                extra.append(prev)
        with multi_tree_lock(self, *extra):
            self._set_attribute_unlocked(key, value)

    def _set_attribute_unlocked(self, key, value):
        if isinstance(key, int):
            old = self.children[key]
            if isinstance(old, dom_tag) and getattr(old, "parent", None) is self:
                old.parent = None
            if isinstance(value, dom_tag):
                prev = getattr(value, "parent", None)
                if prev is not None and prev is not self:
                    try:
                        prev.children.remove(value)
                    except ValueError:
                        pass
                value.parent = self
                value.setdocument(self.document)
            elif isinstance(value, dom_string):
                value.parent = self
            self.children[key] = value
        elif isinstance(key, basestring):
            self.attributes[key] = value
        else:
            raise TypeError(
                "Only integer and string types are valid for assigning "
                "child tags and attributes, respectively."
            )

    __setitem__ = set_attribute

    def delete_attribute(self, key):
        with multi_tree_lock(self):
            self._delete_attribute_unlocked(key)

    def _delete_attribute_unlocked(self, key):
        if isinstance(key, int):
            removed = self.children[key : key + 1]
            del self.children[key : key + 1]
            for obj in removed:
                if isinstance(obj, dom_tag) and getattr(obj, "parent", None) is self:
                    obj.parent = None
        else:
            del self.attributes[key]

    __delitem__ = delete_attribute

    def setdocument(self, doc):
        """
        Creates a reference to the parent document to allow for partial-tree
        validation.
        """
        with multi_tree_lock(self):
            self._setdocument_unlocked(doc)

    def _setdocument_unlocked(self, doc):
        # assume that a document is correct in the subtree
        if self.document != doc:
            self.document = doc
            for child in self:
                if not isinstance(child, dom_tag):
                    continue
                # recursive unlocked to avoid re-locking every level (same root)
                child._setdocument_unlocked(doc)

    def add(self, *args):
        """
        Add new child tags.

        Thread-safe: holds this tree's root lock and any previous parents when
        re-parenting nodes (ordered multi-lock).
        """
        # Only prior parents need cross-tree locks. Orphan children share this
        # tree's lock once attached; locking them as separate roots raced with GC
        # and inflated the lock map under load.
        #
        # Only scan concrete sequences for extras — never generators (one-shot
        # iterators must remain intact for ``_add_unlocked``).
        extras = []
        for obj in args:
            if isinstance(obj, dom_tag):
                prev = getattr(obj, "parent", None)
                if prev is not None and prev is not self:
                    extras.append(prev)
            elif isinstance(obj, (list, tuple)):
                for sub in obj:
                    if isinstance(sub, dom_tag):
                        prev = getattr(sub, "parent", None)
                        if prev is not None and prev is not self:
                            extras.append(prev)
        with multi_tree_lock(self, *extras):
            return self._add_unlocked(*args)

    def _add_unlocked(self, *args):
        for obj in args:
            if obj is None or obj is False:
                # Conditional children (React/Vue-style): skip None / False
                continue
            if obj is True:
                # Bare True is never meaningful DOM content
                continue
            if isinstance(obj, numbers.Number):
                # Convert to string so we fall into next if block
                obj = str(obj)

            if isinstance(obj, basestring):
                # we are going to add the support for escaping only those strings whoes parents
                # have explicit variable "escape_string" set to True
                if hasattr(self, "escape_string"):
                    if self.escape_string:
                        obj = escape(obj)
                else:
                    obj = escape(obj)

                # we are wrapping str into dom_string because when we use .get method we may
                # for some reason want to get the parent of the string values in children,
                # natively its not possible so we wrap str in dom_string and set self as parent

                obj = dom_string(obj) if not isinstance(obj, dom_string) else obj
                obj.parent = self

                self.children.append(obj)

            elif isinstance(obj, dom_tag):
                stack = _peek_with_stack() or []
                for s in stack:
                    s.used.add(obj)

                # Single parent ownership: detach from previous parent if any.
                # Prevents the same node living under two trees (latent corruption).
                prev = getattr(obj, "parent", None)
                if prev is not None and prev is not self:
                    try:
                        prev.children.remove(obj)
                    except ValueError:
                        pass
                if obj in self.children:
                    # already a direct child — keep single entry, refresh parent/doc
                    obj.parent = self
                    obj.setdocument(self.document)
                    continue

                self.children.append(obj)
                obj.parent = self
                obj.setdocument(self.document)

            elif isinstance(obj, dict):
                for attr, value in obj.items():
                    self.set_attribute(*self.clean_pair(attr, value))

            elif hasattr(obj, "__iter__"):
                if not isinstance(obj, type):
                    for subobj in obj:
                        self._add_unlocked(subobj)

            else:  # wtf is it?
                raise ValueError(self.__class__, "%r not a tag or string." % obj)

        if len(args) == 1:
            return args[0]

        return args

    def add_raw_string(self, s):
        with multi_tree_lock(self):
            self.children.append(s)

    def remove(self, obj):
        with multi_tree_lock(self):
            self.children.remove(obj)
            if isinstance(obj, dom_tag) and getattr(obj, "parent", None) is self:
                obj.parent = None

    def clear(self):
        with multi_tree_lock(self):
            self._clear_unlocked()

    def _clear_unlocked(self):
        for i in self.children:
            if isinstance(i, dom_tag) and i.parent is self:
                i.parent = None
        self.children = []

    def replace_children(self, *args):
        """Atomically replace all children (clear + add under one tree lock).

        Prefer this over ``clear()`` then ``add()`` when concurrent renderers
        must never observe an empty intermediate tree.
        """
        extras = []
        for obj in args:
            if isinstance(obj, dom_tag):
                prev = getattr(obj, "parent", None)
                if prev is not None and prev is not self:
                    extras.append(prev)
            elif isinstance(obj, (list, tuple)):
                for sub in obj:
                    if isinstance(sub, dom_tag):
                        prev = getattr(sub, "parent", None)
                        if prev is not None and prev is not self:
                            extras.append(prev)
        with multi_tree_lock(self, *extras):
            self._clear_unlocked()
            if args:
                return self._add_unlocked(*args)
            return args

    @staticmethod
    def _attr_matches(node, attrs):
        """Attribute filter for ``get``.

        * ``value is None`` → presence only (``attr in attributes``), so empty
          string / ``0`` / ``False`` stored values still count as present.
        * otherwise → equality on the cleaned attribute name.
        """
        if not attrs:
            return True
        if not hasattr(node, "attributes"):
            return False
        for attribute, value in attrs:
            if value is None:
                if attribute not in node.attributes:
                    return False
            elif node.attributes.get(attribute) != value:
                return False
        return True

    @staticmethod
    def _type_matches(node, tag):
        """Type / name match for one node (no recursion)."""
        if isinstance(tag, basestring):
            return type(node).__name__ == tag
        if isinstance(tag, type):
            return isinstance(node, tag)
        return False

    def _match_nodes(self, node, tag, attrs):
        """Yield ``node`` (and Component ``_entry`` if distinct) when they match.

        Components are transparent: a ``Card`` that renders a ``div`` must be
        findable as both ``Card`` and ``div`` under MRO / type queries.
        """
        if not isinstance(node, dom_tag):
            return
        candidates = [node]
        entry = getattr(node, "_entry", None)
        # Use identity (``is``) — Component.__eq__ treats Component == _entry
        # as True, which would skip appending the entry to candidates.
        if entry is not None and entry is not node and isinstance(entry, dom_tag):
            candidates.append(entry)

        if isinstance(tag, (basestring, type)) or tag is None:
            type_tag = dom_tag if tag is None else tag
            for cand in candidates:
                if self._type_matches(cand, type_tag) and self._attr_matches(
                    cand, attrs
                ):
                    yield cand
        elif isinstance(tag, dom_tag):
            for cand in candidates:
                # Identity first; optional **attrs still filter the candidate
                if cand is tag and self._attr_matches(cand, attrs):
                    yield cand

    def _find(self, tag=None, **kwargs):
        """Yield matches depth-first (lazy) — no intermediate full lists.

        Prefer this for existence / first-hit. ``get`` is ``list(self._find(...))``.
        """
        if tag is None:
            tag = dom_tag

        attrs = [(self.clean_attribute(attr), value) for attr, value in kwargs.items()]
        seen: set = set()
        direct_children = object.__getattribute__(self, "children")

        def _emit(node):
            nid = id(node)
            if nid in seen:
                return
            seen.add(nid)
            yield node

        for child in direct_children:
            for matched in self._match_nodes(child, tag, attrs):
                yield from _emit(matched)

            if isinstance(child, dom_tag):
                # Descend via child's lazy finder (not child.get → list)
                for found in child._find(tag, **kwargs):
                    yield from _emit(found)

    def get(self, tag=None, **kwargs):
        """Find nodes matching ``tag``/attrs: **own root + entire subtree**.

        Returns a **list** (materialized). For membership / first hit only,
        use ``item in node`` or ``next(node._find(...), None)`` so the walk
        can stop early without building the full result list.

        Unlike ``matches`` (own-only), ``get`` returns every match starting
        from this node's transparent surface (self + Component ``_entry``)
        then all descendants.

        ``tag`` may be class, name string, or **instance** (identity search).

        Consistent pattern::

            c = Card()
            child = ...

            c.get(Card)                   # [c]
            c.get(div)                    # [c._entry]   (and nested divs)
            c.get(span)                   # [title span, ...]
            c.get(id="title")             # [title span]
            c.get(child)                  # [child] if child is under c
            child in c                    # existence only (lazy, short-circuit)
        """
        return list(self._find(tag, **kwargs))

    def __getitem__(self, key):
        """
        Returns the stored value of the specified attribute or child
        (if it exists).
        """
        if isinstance(key, int):
            # Children are accessed using integers
            try:
                return object.__getattribute__(self, "children")[key]
            except KeyError:
                raise IndexError('Child with index "%s" does not exist.' % key)
        elif isinstance(key, basestring):
            # Attributes are accessed using strings
            try:
                return object.__getattribute__(self, "attributes")[key]
            except KeyError:
                raise AttributeError('Attribute "%s" does not exist.' % key)
        else:
            raise TypeError(
                "Only integer and string types are valid for accessing "
                "child tags and attributes, respectively."
            )

    __getattr__ = __getitem__

    def __len__(self):
        """
        Number of child elements.
        """
        return len(self.children)

    def __bool__(self):
        """Node **object** existence — always True.

        A tag instance is a real DOM node even with zero children. Do **not**
        use ``if node`` / ``bool(node)`` to test for children or class
        membership; use::

            if node.matches(div):     # this node is a div (own / MRO)
            if div in node:           # class exists here or in descendants
            if child in node:         # instance exists here or in descendants
            if len(node):             # has children
        """
        return True

    __nonzero__ = __bool__

    def __iter__(self):
        """
        Iterates over child elements.
        """
        return self.children.__iter__()

    def matches(self, tag=None, **kwargs):
        """Scope: **this node only** (plus Component transparent ``_entry``).

        Definition
        ----------
        ``node.matches(tag, **attrs)`` is True iff **at least one** of the
        *candidate faces* of ``node`` satisfies the query. Candidates are:

        1. ``node`` itself
        2. ``node._entry`` if it exists, is a ``dom_tag``, and is not ``node``
           (Component transparency — DOM face of a Component)

        No child, grandchild, or other descendant is ever considered.
        That is the entire scope boundary.

        Query forms
        -----------
        * **class** — ``isinstance(candidate, tag)`` (MRO)
        * **name str** — ``type(candidate).__name__ == tag``
        * **instance** — ``candidate is tag`` (identity, not ``==``)
        * **attrs only** — ``tag is None`` and ``**kwargs``; any candidate
          whose cleaned attributes match
        * **no args** — ``matches()`` → True (node object exists; like
          ``bool(node)``)

        Optional ``**attrs`` always filter candidates (presence if value is
        ``None``, else equality). Applied after class/name/identity.

        Out of scope (use other APIs)
        -----------------------------
        * Descendants → ``get`` / ``in``
        * Child instance under a Component → ``child in card`` or
          ``card.get(child)``, **not** ``card.matches(child)``

        Examples::

            c = Card()                 # faces: Card, _entry div#card-root
            child = c.get(id="title")[0]

            c.matches(Card)            # True  face 1
            c.matches(div)             # True  face 2
            c.matches(c)               # True  identity face 1
            c.matches(c._entry)        # True  identity face 2
            c.matches(span)            # False neither face is span
            c.matches(child)           # False child is not a face of c
            c.matches(div, id="card-root")   # True
            c.matches(c._entry, id="nope")   # False (attrs fail)
            child.matches(span)        # True  ask the child (its own scope)
        """
        if tag is None and not kwargs:
            # No criteria → the node itself exists (same idea as __bool__)
            return True
        type_tag = dom_tag if tag is None else tag
        attrs = [(self.clean_attribute(attr), value) for attr, value in kwargs.items()]
        for _ in self._match_nodes(self, type_tag, attrs):
            return True
        return False

    def __contains__(self, item):
        """``item in node`` ≡ own match **or** a hit under the subtree.

        Short-circuits on the first match — does **not** build a full
        ``get()`` list (memory-safe for large trees)::

            child in Card()     # True if child is Card, Card._entry, or under it
            span in Card()      # True if Card/entry is span OR any descendant is

        Equivalent::

            child in node  ⇔  next(node._find(child), None) is not None
            # after own-instance / own-face fast paths
        """
        # --- own existence (instance or class / name) ---
        if isinstance(item, dom_tag):
            if item is self:
                return True
            entry = getattr(self, "_entry", None)
            if entry is not None and item is entry:
                return True
        if isinstance(item, (basestring, type, dom_tag)):
            if any(self._match_nodes(self, item, [])):
                return True
        elif item is None:
            return False
        else:
            return False

        # --- descendant existence (lazy; stop at first hit) ---
        for _ in self._find(item):
            return True
        return False

    def __iadd__(self, obj):
        """
        Reflexive binary addition simply adds tag as a child.
        """
        self.add(obj)
        return self

    # String and unicode representations are the same as __render__()
    def __unicode__(self):
        return self.__render__()

    __str__ = __unicode__

    def __render__(self, indent="  ", pretty=True, xhtml=False):
        """Phase **serialize** (sync): walk the finished tree → HTML string.

        Does **not** call ``__enter__`` / ``__exit__``. Those only run while
        *building* the tree (``with tag:``). Typical pipeline::

            with div() as root:          # __enter__ / __exit__
                span("x")
            html = root.__render__()     # serialize only

        Thread-safe: holds the tree root lock for a consistent snapshot.
        """
        with multi_tree_lock(self):
            html_tokens = self._render([], 0, indent, pretty, xhtml)
            return "".join(html_tokens)

    def _walk_render_tokens(self, indent_level, indent_str, pretty, xhtml, _seen=None):
        """Yield HTML tokens while walking the tree (sync generator).

        Subclasses (Tags) may override for true open→children→close streaming.
        Default falls back to full ``_render`` token list.
        """
        yield from self._render(
            [], indent_level, indent_str, pretty, xhtml, _seen=_seen
        )

    async def __async_render__(
        self,
        indent="  ",
        pretty=True,
        xhtml=False,
        *,
        chunk_size: int = 8,
    ):
        """Phase **serialize** (async): walk the finished tree → token stream.

        Does **not** call ``__aenter__`` / ``__aexit__``. Those only run while
        *building* the tree (``async with tag:``). Typical pipeline::

            async with div() as root:                 # __aenter__ / __aexit__
                span("x")
            async for tok in root.__async_render__():  # serialize only
                ...

        Trees built with sync ``with`` can also be streamed here (and the reverse
        works: async-built trees can use ``__render__``). Construction mode and
        serialization mode are independent; the recommended pairing is:

        * sync build (``with``) → ``__render__`` or sync token walk
        * async build (``async with``) → ``__async_render__`` stream

        Thread-safe & await-safe: tokens are snapshotted under the tree lock
        (same generation as sync ``__render__``), then yielded **without**
        holding the lock across ``await`` points.
        """
        import asyncio

        with multi_tree_lock(self):
            tokens = list(self._walk_render_tokens(0, indent, pretty, xhtml))
        n = 0
        for html_token in tokens:
            yield html_token
            n += 1
            if chunk_size and n % chunk_size == 0:
                await asyncio.sleep(0)

    def _render(
        self, sb, indent_level=0, indent_str="  ", pretty=True, xhtml=False, _seen=None
    ):
        # Cycle guard: parent.add(child); child.add(parent) must not blow the stack
        if _seen is None:
            _seen = set()
        sid = id(self)
        if sid in _seen:
            sb.append("<!--cycle:%s-->" % type(self).__name__)
            return sb
        _seen.add(sid)

        pretty = pretty and self.is_pretty

        name = getattr(self, "tagname", type(self).__name__)

        # Workaround for python keywords and standard classes/methods
        # (del, object, input)
        if name[-1] == "_":
            name = name[:-1]
        if name[0] == "_":
            name = name[1:]

        # open tag
        sb.append("<")
        sb.append(name)

        for attribute, value in sorted(self.attributes.items()):
            if value is not False:  # False values must be omitted completely
                sb.append(' %s="%s"' % (attribute, escape(unicode(value), True)))

        sb.append(" />" if self.is_single and xhtml else ">")

        if not self.is_single:
            inline = self._render_children(
                sb, indent_level + 1, indent_str, pretty, xhtml, _seen=_seen
            )

            if pretty and not inline:
                sb.append("\n")
                sb.append(indent_str * indent_level)

            # close tag
            sb.append("</")
            sb.append(name)
            sb.append(">")

        return sb

    def _render_children(self, sb, indent_level, indent_str, pretty, xhtml, _seen=None):
        inline = True
        for child in self:
            if isinstance(child, dom_tag):
                if pretty and not child.is_inline:
                    inline = False
                    sb.append("\n")
                    sb.append(indent_str * indent_level)
                child._render(sb, indent_level, indent_str, pretty, xhtml, _seen=_seen)
            else:
                sb.append(unicode(child))

        return inline

    def __repr__(self):
        name = "%s.%s" % (self.__module__, type(self).__name__)

        attributes_len = len(self.attributes)
        attributes = "%s attribute" % attributes_len
        if attributes_len != 1:
            attributes += "s"

        children_len = len(self.children)
        children = "%s child" % children_len
        if children_len != 1:
            children += "ren"

        return "<%s at %x: %s, %s>" % (name, id(self), attributes, children)

    @classmethod
    def clean_attribute(cls, attribute):
        """
        Normalize attribute names for shorthand and work arounds for limitations
        in Python's syntax
        """

        # Shorthand
        attribute = {
            "cls": "class",
            "className": "class",
            "classname": "class",
            "classes": "class",
            "class_name": "class",
            "fr": "for",
            "html_for": "for",
            "htmlFor": "for",
            "for_": "for",
            "class_": "class",
        }.get(attribute, attribute)

        # Workaround for Python's reserved words
        if attribute[0] == "_":
            attribute = attribute[1:]

        # Workaround for dash
        special_prefix = any([attribute.startswith(x) for x in ("data_", "aria_")])
        if attribute in {"http_equiv"} or special_prefix:
            attribute = attribute.replace("_", "-")

        # Workaround for colon
        if attribute.split("_")[0] in ("xlink", "xml", "xmlns"):
            attribute = attribute.replace("_", ":", 1)

        return attribute

    @classmethod
    def clean_pair(cls, attribute, value):
        """
        This will call `clean_attribute` on the attribute and also allows for the
        creation of boolean attributes.

        Ex. input(selected=True) is equivalent to input(selected="selected")
        """
        attribute = cls.clean_attribute(attribute)

        # Check for boolean attributes
        # (i.e. selected=True becomes selected="selected")
        if value is True:
            # HTML boolean attrs use name=name; WC flags need "true" for JS.
            if attribute in {
                "shadowdom",
                "shadowroot",
                "shadow-root",
            }:
                value = "true"
            else:
                value = attribute

        # Ignore `if value is False`: this is filtered out in render()

        return (attribute, value)


_get_current_none = object()


def get_current(default=_get_current_none):
    """Current tag in the active build stack (sync with or async with).

    ContextVar-backed — correct for threads and asyncio Tasks.
    """
    if _WITH_STACK is not None:
        stack = _WITH_STACK.get()
    else:
        stack = None
    if stack:
        return stack[-1].tag
    if default is _get_current_none:
        raise ValueError("no current context")
    return default


def attr(*args, **kwargs):
    """
    Set attributes on the current active tag context
    """
    c = get_current()
    dicts = args + (kwargs,)
    for d in dicts:
        for attr, value in d.items():
            c.set_attribute(*c.clean_pair(attr, value))


# escape() is used in render
from ux_dom.dom.src.utils.dom_util import escape
