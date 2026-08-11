# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

"""Component, Fragment, ReactiveComponent — application building blocks.

* Component: render() returns a DOM tree; dataclass fields supported.
* Fragment: invisible shell (render_tag=False); unique attrs applied once.
* ReactiveComponent: field mutation re-renders; fail-closed rollback on error.

Concurrent mutate/serialize uses per-root locks via dom_tag paths.
See docs/guides/COMPONENTS.md and docs/guides/REACTIVE.md.
"""
from __future__ import annotations

import json
import warnings
from dataclasses import asdict, dataclass, field
from html import unescape
from pathlib import Path
from textwrap import dedent
from typing import Iterable, List, Union

from marko import convert as markdown

from ux_dom.dom.src import csstags, htmltags, jinjatags, svgtags
from ux_dom.dom.src.concurrency import multi_tree_lock
from ux_dom.dom.src.dom_tag import dom_tag
from ux_dom.dom.src.html_string import defHTML
from ux_dom.dom.src.main import extension
from ux_dom.utils.parameters import Parameters

__all__ = ["Component", "ReactiveComponent", "Fragment", "MergeClassAttribute"]



@dataclass
class Component(extension.Tags):
    """Composable UI unit: implement ``render`` and return a DOM tree.

    ``@dataclass`` subclasses are supported — field assignment runs, then
    ``render`` builds the tree (lazy init chain). Prefer explicit fields::

        @dataclass(eq=False)
        class Card(Component):
            title: str
            def render(self, title):
                return div(title)
    """

    left_delimiter = "<"
    right_delimiter = ">"
    css_tags = csstags
    svg_tags = svgtags
    html_tags = htmltags
    jinja_tags = jinjatags
    file_extension: str = field(init=False, default=".html")
    render_tag: bool = field(init=False, default=False)
    attributes: dict = field(init=False, default_factory=dict)
    children: List[Union[str, "dom_tag"]] = field(init=False, default_factory=list)
    parent: Union["dom_tag", None] = field(init=False, default=None)
    document: Union["dom_tag", None] = field(init=False, default=None)
    files_directory: Union[str, Path, None] = field(init=False, default=None)
    escape_string: bool = field(init=False, default=True)
    string_is_markdown: bool = field(init=False, default=False)

    # Route classmethods often use HTTP verb names (get/add/clear/...). Those
    # must remain on the *class* for DirectoryRouter, but must NOT shadow the
    # DOM tree API on *instances*. Instance lookup skips subclass classmethods
    # for this reserved set and binds the Component/dom implementation.
    _DOM_INSTANCE_API = frozenset(
        {
            "add",
            "get",
            "clear",
            "remove",
            "matches",
            "set_attribute",
            "delete_attribute",
            "setdocument",
            "add_raw_string",
        }
    )

    def __getattribute__(self, name: str):
        if name == "_DOM_INSTANCE_API" or name.startswith("__"):
            return object.__getattribute__(self, name)
        try:
            reserved = object.__getattribute__(self, "_DOM_INSTANCE_API")
        except AttributeError:
            reserved = ()
        if name in reserved:
            # Prefer the first non-classmethod implementation in the MRO
            # starting from Component (this class) so route @classmethods on
            # subclasses cannot shadow tree operations.
            cls = object.__getattribute__(self, "__class__")
            for base in cls.__mro__:
                if name not in base.__dict__:
                    continue
                attr = base.__dict__[name]
                if isinstance(attr, classmethod):
                    continue
                if isinstance(attr, staticmethod):
                    return attr.__get__(self, cls)
                if isinstance(attr, property):
                    return attr.__get__(self, cls)
                if callable(attr):
                    return attr.__get__(self, cls)
        return object.__getattribute__(self, name)

    # NOTE: do not key off id(cls) — CPython reuses ids after GC and would
    # skip wrapping a new dataclass Component (empty render under long suites).

    @staticmethod
    def _ensure_init_chain(cls: type) -> None:
        """Wrap dataclass-generated ``__init__`` so ``render`` still runs.

        ``@dataclass class X(Component)`` replaces ``Component.__init__`` after
        class creation, so chaining runs lazily on first instantiation.
        """
        if cls is Component:
            return
        # Already wrapped for *this* class object
        if getattr(cls.__dict__.get("__init__"), "_ux_dom_component_chained", False):
            return
        if getattr(cls.__init__, "_ux_dom_component_chained", False):  # type: ignore[misc]
            return
        orig = cls.__dict__.get("__init__")
        if orig is None or orig is Component.__init__:
            return

        component_init = Component.__init__

        def __init__(self, *args, **kwargs):
            orig(self, *args, **kwargs)
            try:
                entry = object.__getattribute__(self, "_entry")
            except AttributeError:
                entry = None
            try:
                children = object.__getattribute__(self, "children")
            except AttributeError:
                children = None
            if entry is not None or (children is not None and len(children) > 0):
                return
            field_kwargs = {}
            try:
                import dataclasses as _dc

                for f in _dc.fields(self):
                    if f.init:
                        try:
                            field_kwargs[f.name] = object.__getattribute__(self, f.name)
                        except AttributeError:
                            pass
            except (TypeError, Exception):
                pass
            component_init(self, **field_kwargs)

        __init__._ux_dom_component_chained = True  # type: ignore[attr-defined]
        cls.__init__ = __init__  # type: ignore[method-assign,misc]

    def __new__(cls, *args, **kwargs):
        Component._ensure_init_chain(cls)
        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        super(Component, self).__init__()

        # Local converter only — never mutate module-global markdown
        md_convert = kwargs.pop("markdown", None) or markdown
        md_convert = getattr(md_convert, "convert", md_convert)
        # first we get the child from the render method and sanitize it.
        child = self.render(*args, **kwargs)

        if child is None:
            raise ValueError(
                f"{self.__class__.__name__} `render` method must return a value."
            )

        if isinstance(child, str):
            if self.string_is_markdown:
                child = (
                    md_convert(child)
                    if self.escape_string
                    else unescape(md_convert(child))
                )
            child = defHTML(child, escape=self.escape_string)

        elif isinstance(child, Path):
            string_is_markdown = child.suffix == ".md"
            child = self._from_file(child)
            if string_is_markdown:
                child = (
                    md_convert(child)
                    if self.escape_string
                    else unescape(md_convert(child))
                )
            child = defHTML(child, escape=self.escape_string)

        if isinstance(child, (list, tuple)) and len(child) == 1:
            child = child[0]
        # commented and shifted __init__ below to the first line because then Fragment can
        # add *args and **kwargs on initialization inside render method
        # super(Component, self).__init__()

        if child is not self:
            # Prefer DOM add even if subclass defines route classmethod ``add``
            Component.add(self, child)

        self._entry = self if isinstance(child, (list, tuple)) else child

        # we perform checks on the _entry "after" the dom initialization because .get method
        # looks into children
        self.__checks__(self._entry)

    def __checks__(
        self, element: Union[dom_tag, extension.Tags]
    ) -> Union[dom_tag, extension.Tags]:  # noqa
        if self.render_tag:
            raise ValueError(f"{self.render_tag=} can not be true for Components")
        return element

    def add(self, *args):
        """
        Adding tags to a component appends them to the render.
        """
        if not self.render_tag and hasattr(self, "_entry") and self._entry is not self:
            return self._entry.add(*args)
        return super().add(*args)

    def set_attribute(self, key, value):
        if not self.render_tag and hasattr(self, "_entry") and self._entry is not self:
            self._entry.set_attribute(key, value)
        else:
            super(Component, self).set_attribute(key, value)

    __setitem__ = set_attribute

    def delete_attribute(self, key):
        if not self.render_tag and hasattr(self, "_entry") and self._entry is not self:
            self._entry.delete_attribute(key)
        else:
            super(Component, self).delete_attribute(key)

    __delitem__ = delete_attribute

    def get(self, tag=None, **kwargs):
        """Search this Component: match self + ``_entry``, then descendants.

        Previously only ``_entry.get(...)`` ran, which **skipped the entry
        node itself** — so ``parent.get(div)`` failed when a Component rendered
        a ``div``. Membership / MRO queries now see the transparent root.
        """
        if not self.render_tag and hasattr(self, "_entry") and self._entry is not self:
            if tag is None:
                tag = dom_tag
            attrs = [
                (self.clean_attribute(attr), value) for attr, value in kwargs.items()
            ]
            results = []
            # Match Component and/or its rendered root
            for matched in self._match_nodes(self, tag, attrs):
                if all(matched is not r for r in results):
                    results.append(matched)
            # Descend into the entry's children (entry itself already considered)
            for found in self._entry.get(tag, **kwargs):
                if all(found is not r for r in results):
                    results.append(found)
            return results
        return super(Component, self).get(tag, **kwargs)

    def __contains__(self, item):
        """Own class/instance existence + subtree (see ``dom_tag``)."""
        return super().__contains__(item)

    def __getitem__(self, key):
        if not self.render_tag:
            entry = None
            try:
                entry: Union[dom_tag, extension.Tags] = object.__getattribute__(
                    self, "_entry"
                )
            except AttributeError:
                pass
            if entry and entry is not self:
                return entry.__getitem__(key)

        return super(Component, self).__getitem__(key)

    __getattr__ = __getitem__

    def clear(self):
        if not self.render_tag and hasattr(self, "_entry") and self._entry is not self:
            self._entry.clear()
        else:
            super().clear()

    def __len__(self):
        if not self.render_tag and hasattr(self, "_entry") and self._entry is not self:
            return len(self._entry)
        return super().__len__()

    def __iter__(self):
        if not self.render_tag and hasattr(self, "_entry") and self._entry is not self:
            return self._entry.__iter__()
        return super().__iter__()

    def __hash__(self) -> int:
        # **DON'T create** hash with self._entry that is hash(self._entry),
        # inside __exit__ stack frame has a 'set' of used tags. it uses
        # hash to check membership. if we use it like below the Component
        # classes will be skipped. SO PLEASE DON'T CHANGE IT. I wasted
        # 3 days for this simple issue with lots of head scratching.
        # if hasattr(self, "_entry") and self._entry is not self:
        #     return hash(self._entry)
        return super().__hash__()

    def __eq__(self, other) -> bool:
        if not self.render_tag and hasattr(self, "_entry") and self._entry is not self:
            # now check if the other isinstance of Component
            if (
                isinstance(other, Component)
                and not other.render_tag
                and hasattr(other, "_entry")
                and other._entry is not other
            ):
                return self._entry is other._entry
            return self._entry is other
        else:
            if (
                isinstance(other, Component)
                and not other.render_tag
                and hasattr(other, "_entry")
                and other._entry is not other
            ):
                return self is other._entry
            return self is other

    def _asdict(self, exclude=None) -> dict:
        exclude = exclude or [
            "file_extension",
            "render_tag",
            "children",
            "document",
            "parent",
            "attributes",
            "files_directory",
            "escape_string",
            "string_is_markdown",
        ]
        return {key: value for key, value in asdict(self).items() if key not in exclude}

    def to_dict(self, exclude=None) -> dict:
        return self._asdict(exclude=exclude)

    def render(self, *args, **kwargs) -> Union[dom_tag, extension.Tags, str]:  # noqa
        raise NotImplementedError(
            f"{self.__class__.__name__}.{self.render.__name__} method not implemented"
        )

    @classmethod
    def _from_file(cls, file_name: Union[str, Path]) -> str:
        file_location = None

        if isinstance(cls.files_directory, Path):
            if not cls.files_directory.exists():
                raise FileNotFoundError(f"file {cls.files_directory=} does not exists")

            if not cls.files_directory.is_dir():
                raise ValueError(f"{cls.files_directory=} is not a directory")

            file_location = cls.files_directory / file_name

        elif cls.files_directory:
            if not isinstance(cls.files_directory, str):
                raise ValueError(f"{cls.files_directory=} is not str")

            cls.files_directory = Path(cls.files_directory)

            if not cls.files_directory.exists():
                raise FileNotFoundError(f"file {cls.files_directory=} does not exists")

            if not cls.files_directory.is_dir():
                raise ValueError(f"{cls.files_directory=} is not a directory")

            file_location = cls.files_directory / file_name

        else:
            file_location = Path(file_name) if isinstance(file_name, str) else file_name

        if not file_location.exists():
            raise FileNotFoundError(f"{file_location} does not exists")

        if not file_location.is_file():
            raise ValueError(f"{file_location} is not a file")

        return file_location.read_text()

    @classmethod
    def from_file(cls, file_name: Union[str, Path]) -> "Component":
        return cls(cls._from_file(file_name))

    def script(self, *args, **kwargs): ...

    def call(self, *args, **kwargs):
        """
        This is basically a placeholder for using websocket communications.
        All sorts of fun stuffs can happens here.
        :param args:
        :param kwargs:
        :return:
        """

        raise NotImplementedError(f"method: {self.call.__qualname__} not implemented")

    def __dir__(self) -> Iterable[str]:
        return sorted(iter(self.__dict__), key=lambda k: k)


class Fragment(Component):
    """Transparent group: renders children only, fans attributes onto them.

    Shared attrs (``class``, ``x-data``, ``@click``, …) apply to **each** child.
    Unique attrs (``id``) apply only to the **first** child — duplicating ``id``
    across siblings is invalid HTML and is intentionally avoided.
    """

    render_tag = False

    # Attributes that must not be fanned out to every child (invalid HTML / form bugs)
    _UNIQUE_CHILD_ATTRS = frozenset({"id"})

    def _add_attrs_to_child(
        self,
        child: Union[extension.Tags, dom_tag],
        *,
        apply_unique: bool = True,
    ):
        # here we are adding safe_attributes because we need a way to bypass
        # escaping of attribute values for

        if hasattr(child, "safe_attributes"):
            child.safe_attributes.update(self.safe_attributes)

        for attr, value in self.attributes.items():
            # Multi-child fragments: only the first child may receive unique attrs
            # (duplicate id= is invalid HTML and breaks getElementById / labels).
            if not apply_unique and attr in self._UNIQUE_CHILD_ATTRS:
                continue
            # ===================================================================
            # --------------------------^ x-data section ------------------------
            # ===================================================================
            # merging x-data attr from Fragment class to child class
            if attr == "x-data" and child.attributes.get(attr, None):
                # Fail closed: invalid JSON must not crash the tree build
                try:
                    raw_child = child.attributes.get(attr)
                    x_data = json.loads(str(raw_child).replace("'", '"'))
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    warnings.warn(
                        f"{self.__class__.__name__}: child x-data is not JSON "
                        f"({exc}); skipping x-data merge",
                        stacklevel=2,
                    )
                    continue
                if value is None:
                    value = x_data
                else:
                    try:
                        value = json.loads(str(value).replace("'", '"'))
                    except (json.JSONDecodeError, TypeError, ValueError) as exc:
                        warnings.warn(
                            f"{self.__class__.__name__}: fragment x-data is not JSON "
                            f"({exc}); keeping child x-data only",
                            stacklevel=2,
                        )
                        continue
                if isinstance(x_data, dict) and isinstance(value, dict):
                    value = x_data | value

                value = json.dumps(value).replace('"', "'")
            # ===================================================================
            # --------------------------$ x-data section ------------------------
            # ===================================================================

            # ===================================================================
            # --------------------------^ class section -------------------------
            # ===================================================================
            # merging class attr from Fragment class to child class
            if attr == "class" and child.attributes.get(attr, None):
                value = " ".join([child.attributes[attr], value])

            # ===================================================================
            # --------------------------$ class section -------------------------
            # ===================================================================

            # ===================================================================
            # --------------------------^ x-on @ event section ------------------
            # ===================================================================
            # merging event attr (starting with @) from Fragment class to child
            # class
            if attr.startswith("@") and child.attributes.get(attr, None):
                # remove indentation and any newlines from the child attribute value
                child_attr_value = " ".join(
                    map(lambda x: x.strip(), dedent(child.attributes[attr]).split("\n"))
                )

                value = "; ".join([child_attr_value, value])
            # ===================================================================
            # --------------------------$ x-on @ event section ------------------
            # ===================================================================

            # ===================================================================
            # --------------------------^ x-tansition section -------------------
            # ===================================================================
            # merging x-tansition from Fragment class to child class
            if attr.startswith("x-transition") and child.attributes.get(attr, None):
                if value:
                    value = " ".join([child.attributes[attr], value])
            # ===================================================================
            # --------------------------^ x-tansition section -------------------
            # ===================================================================

            # ===================================================================
            # --------------------------^ x-bind : section ----------------------
            # ===================================================================
            if attr.startswith(":") and child.attributes.get(attr, None):
                warnings.warn(
                    message=f"{self.__class__.__name__} has not implemented merging attribute: x-bind"
                )

            child.set_attribute(*child.clean_pair(attr, value))

    def add(self, *args):
        # First *tag* child may receive id=; further siblings get shared attrs only.
        apply_unique = not getattr(self, "_ux_dom_frag_unique_applied", False)
        for arg in args:
            if isinstance(arg, (extension.Tags, dom_tag)):
                self._add_attrs_to_child(arg, apply_unique=apply_unique)
                if apply_unique:
                    object.__setattr__(self, "_ux_dom_frag_unique_applied", True)
                    apply_unique = False
            elif isinstance(arg, (list, tuple)):
                for item in arg:
                    if isinstance(item, (extension.Tags, dom_tag)):
                        self._add_attrs_to_child(item, apply_unique=apply_unique)
                        if apply_unique:
                            object.__setattr__(self, "_ux_dom_frag_unique_applied", True)
                            apply_unique = False
        super().add(*args)

    def render(self, *args, **kwargs):
        self.add(kwargs)
        [
            self.add(defHTML(arg)) if isinstance(arg, str) else self.add(arg)
            for arg in args
        ]

        # for this component to behave as a fragment we must simply return self
        # Component class will take care of all the things itself.
        return self


class MergeClassAttribute(Fragment):
    """Merging the attributes with subcontexts via ux_dom.dom.src.dom_tag.attr

    Args:
        None:
    Usage:
        with MergeClassAttribute():
            attr(className=...)
            attr(className=...)
            div()
            ### this div receives all the attributes set via attr methods contexts
            ### but all the className kwargs are merged..

    """

    def _merge_class_attr(self, key, value):
        if key == "class" and self.attributes.get(key, None):
            value = " ".join([self.attributes[key], value])
        return key, value

    def set_attribute(self, key, value):
        if key == "class":
            key, value = self._merge_class_attr(key, value)

        super().set_attribute(key, value)

    __setitem__ = set_attribute


@dataclass(eq=False)
class ReactiveComponent(Component):
    """Component that re-renders when field state changes.

    Intended usage (dataclass fields are the reactive state)::

        @dataclass(eq=False)
        class Counter(ReactiveComponent):
            count: int = 0

            def render(self, count=0):
                return div(str(count))

            def increment(self):
                self.count += 1

        c = Counter(count=1)
        c.increment()
        assert "2" in str(c)

    Also supports the pattern that calls ``super().__init__`` from
    a custom ``__post_init__``.

    State is stored on ``_ux_dom_states`` via ``object.__setattr__`` so it never
    goes through DOM ``__getitem__`` / attribute lookup (the old ``__states``
    name-mangled path broke under dataclass ``__post_init__``).

    Safety (0.1 hardening)
    ----------------------
    * ``render()`` runs **before** the old tree is cleared — exceptions leave
      the previous tree intact.
    * Multi-root renders (list/tuple) keep ``_entry is self`` (never a bare list).
    * Re-entrancy during update is ignored (no recursive re-render storms).
    * Parent slot is restored after re-render; single-root extra children are
      preserved when possible.
    """

    def __init__(self, *args, **kwargs):
        # Constructor kwargs (attrs + field overrides) seed reactive state
        object.__setattr__(self, "_ux_dom_states", dict(kwargs))
        super(ReactiveComponent, self).__init__(*args, **kwargs)
        self._snapshot_states()

    def __post_init__(self, *args, **kwargs):
        """Dataclass hook: ensure render ran, then snapshot field state.

        Subclasses that override ``__post_init__`` should call
        ``super().__post_init__()`` *or* ``super().__init__(...)``.
        """
        # Tests may call super().__init__ from their own __post_init__;
        # if _entry already exists we only refresh the snapshot.
        if not hasattr(self, "_entry") or getattr(self, "_entry", None) is None:
            try:
                field_kwargs = self.to_dict()
            except Exception:
                field_kwargs = {}
            # Prefer already-set _ux_dom_states (constructor path)
            try:
                seed = object.__getattribute__(self, "_ux_dom_states")
            except AttributeError:
                seed = {}
            merged = {**seed, **field_kwargs}
            object.__setattr__(self, "_ux_dom_states", merged)
            Component.__init__(self, **merged)
        self._snapshot_states()

    def _snapshot_states(self) -> None:
        try:
            current = self.to_dict()
        except Exception:
            current = {}
        try:
            prev = object.__getattribute__(self, "_ux_dom_states")
        except AttributeError:
            prev = {}
        if not isinstance(prev, dict):
            prev = {}
        object.__setattr__(self, "_ux_dom_states", {**prev, **current})

    def _get_states(self) -> dict:
        try:
            st = object.__getattribute__(self, "_ux_dom_states")
        except AttributeError:
            st = {}
            object.__setattr__(self, "_ux_dom_states", st)
        if not isinstance(st, dict):
            st = {}
            object.__setattr__(self, "_ux_dom_states", st)
        return st

    def _get_param(self, function, new_kwargs):
        param = Parameters(function, in_single_kwargs=False)
        _arg_dict, _kwarg_dict = param.parameters
        var_arg_name = param.var_arg_name
        arg_dict = {k: new_kwargs.get(k, v) for k, v in _arg_dict.items()}
        kwargs = {k: new_kwargs.get(k, v) for k, v in _kwarg_dict.items()}
        args = []
        for arg_name in arg_dict:
            arg_val = arg_dict[arg_name]
            if (
                param.default(arg_name) is param.empty
                and arg_name not in new_kwargs
                and not any([arg_val])
            ):
                raise ValueError(
                    f"{arg_name} is a required parameter for {function.__name__}"
                )
            else:
                if isinstance(arg_val, tuple) and arg_name == var_arg_name:
                    args.extend(arg_val)
                else:
                    args.append(arg_val)
        return args, kwargs

    def _render_call(self, states: dict):
        """Invoke ``render`` with resolved args/kwargs from state dict."""
        args, kwargs = self._get_param(self.render, states)
        if args and kwargs:
            return self.render(*args, **kwargs)
        if args:
            return self.render(*args)
        if kwargs:
            return self.render(**kwargs)
        return self.render()

    def _attach_render_result(self, elements) -> None:
        """
        Attach ``render()`` output the same way ``Component.__init__`` does.

        Critical: multi-root (list/tuple) must set ``_entry = self``, never a bare
        list — otherwise re-render and membership break (AttributeError on .add).
        """
        child = elements
        if child is None:
            raise ValueError(
                f"{self.__class__.__name__} `render` method must return a value."
            )
        if isinstance(child, (list, tuple)) and len(child) == 1:
            child = child[0]
        if child is self:
            self._entry = self
            return
        # Multi-root fragment: entry face is the component itself
        if isinstance(child, (list, tuple)):
            Component.add(self, child)
            self._entry = self
            return
        Component.add(self, child)
        self._entry = child

    def _re_render(self, **states) -> extension.Tags:  # noqa
        """
        Rebuild tree from current state.

        * Preserves parent slot index.
        * Preserves children appended onto a single-root entry after first render.
        * Renders **before** clearing so a failed ``render`` leaves the old tree.
        * Never assigns a bare list to ``_entry``.
        """
        old_parent = self.parent
        old_entry = getattr(self, "_entry", None)
        old_self_children = list(getattr(self, "children", []) or [])
        old_entry_children: list = []
        single_root = (
            old_entry is not None
            and old_entry is not self
            and not isinstance(old_entry, (list, tuple))
        )
        if single_root and old_entry is not None:
            try:
                old_entry_children = list(getattr(old_entry, "children", []) or [])
            except Exception:
                old_entry_children = []

        index_of_entry = None
        if old_parent is not None:
            try:
                index_of_entry = old_parent.children.index(self)
            except ValueError:
                index_of_entry = None

        # Call render first — fail closed without destroying the previous tree
        try:
            elements = self._render_call(states)
        except Exception:
            raise

        # Commit: replace tree
        try:
            self.clear()
            if (
                old_entry is not None
                and old_entry is not self
                and hasattr(self, "_entry")
            ):
                try:
                    del self._entry
                except Exception:
                    pass
            # clear again if del left residue
            if getattr(self, "children", None):
                self.clear()

            self._attach_render_result(elements)

            # Restore extras that were add()'d onto the previous single-root entry
            # after its original render children (same semantics as before).
            if (
                single_root
                and old_entry_children
                and getattr(self, "_entry", None) is not None
                and self._entry is not self
            ):
                try:
                    new_entry_children = list(self._entry.children)
                except Exception:
                    new_entry_children = []
                unadded = old_entry_children[len(new_entry_children) :]
                if unadded:
                    try:
                        self._entry.add(unadded)
                    except Exception:
                        for node in unadded:
                            try:
                                self._entry.add(node)
                            except Exception:
                                pass

            if old_parent is not None and index_of_entry is not None:
                try:
                    old_parent.set_attribute(index_of_entry, self)
                except Exception:
                    # best-effort re-parent
                    try:
                        if self not in getattr(old_parent, "children", []):
                            old_parent.add(self)
                    except Exception:
                        pass

            return getattr(self, "_entry", self)
        except Exception:
            # Rollback to previous tree so the component stays usable
            try:
                self.clear()
                if hasattr(self, "_entry"):
                    try:
                        del self._entry
                    except Exception:
                        pass
                if old_entry is self or (
                    isinstance(old_self_children, list) and old_entry is None
                ):
                    # multi-root / self-entry: restore children
                    self._entry = self
                    for node in old_self_children:
                        try:
                            extension.Tags.add(self, node)
                        except Exception:
                            try:
                                super(Component, self).add(node)
                            except Exception:
                                pass
                elif old_entry is not None and not isinstance(old_entry, (list, tuple)):
                    try:
                        extension.Tags.add(self, old_entry)
                    except Exception:
                        Component.add(self, old_entry)
                    self._entry = old_entry
                    if old_entry_children and not list(getattr(old_entry, "children", []) or []):
                        for node in old_entry_children:
                            try:
                                old_entry.add(node)
                            except Exception:
                                pass
                else:
                    # last resort: re-attach any known children
                    for node in old_self_children:
                        try:
                            extension.Tags.add(self, node)
                        except Exception:
                            pass
                    self._entry = self if old_self_children else old_entry

                if old_parent is not None and index_of_entry is not None:
                    try:
                        old_parent.set_attribute(index_of_entry, self)
                    except Exception:
                        pass
            except Exception:
                pass
            raise

    def _check_states_and_update(self) -> None:
        """Re-render when dataclass field snapshot differs from last commit.

        On ``render`` failure the previous tree is kept **and** ``_ux_dom_states``
        is rolled back so field values stay consistent with what is displayed.

        Uses the shared per-tree ``RLock`` (see ``ux_dom.dom.src.concurrency``)
        so concurrent mutation, re-render, and serialize on the same tree never
        tear state. Re-entrant for nested clear/add; updating flag blocks storms.
        """
        # Same tree lock as DOM mutation/serialize — one lock domain, no deadlock
        # with clear/add during re-render (RLock re-entrant).
        with multi_tree_lock(self):
            self._check_states_and_update_locked()

    def _check_states_and_update_locked(self) -> None:
        # Re-entrancy guard: nested set_attribute / render must not recurse
        if getattr(self, "_ux_dom_reactive_updating", False):
            return
        try:
            current_states = self.to_dict()
        except Exception:
            current_states = {}
        original_states = dict(self._get_states())

        merged = original_states | current_states
        if merged == original_states:
            # Still refresh snapshot identity for deep-copied values from asdict
            object.__setattr__(self, "_ux_dom_states", merged)
            return

        object.__setattr__(self, "_ux_dom_reactive_updating", True)
        try:
            object.__setattr__(self, "_ux_dom_states", merged)
            try:
                self._re_render(**merged)
            except Exception:
                # Roll state back to last successful commit (tree already restored
                # inside _re_render). Without this, b.n stays at the failed value
                # while the DOM still shows the previous tree — a silent desync.
                object.__setattr__(self, "_ux_dom_states", dict(original_states))
                # Also restore dataclass field attributes to match rolled-back state
                for key, val in original_states.items():
                    try:
                        if key in getattr(self, "__dataclass_fields__", {}):
                            object.__setattr__(self, key, val)
                    except Exception:
                        pass
                raise
        finally:
            object.__setattr__(self, "_ux_dom_reactive_updating", False)

    def set_attribute(self, key, value):
        # DOM attribute writes should not silently skip pending field re-renders
        self._check_states_and_update()
        super().set_attribute(key=key, value=value)

    __setitem__ = set_attribute

    def _render(
        self,
        sb,
        indent_level=1,
        indent_str="  ",
        pretty=True,
        xhtml=False,
        _seen=None,
    ):
        self._check_states_and_update()
        return super()._render(sb, indent_level, indent_str, pretty, xhtml, _seen=_seen)
