# Copyright (c) 2022–2026 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""HTML / custom-element component bases for ux-dom.

XElement contract (one name · one attribute · one runtime)
==========================================================

+------------------+---------------------------+----------------------------------+
| Role             | Name                      | Notes                            |
+==================+===========================+==================================+
| Python base      | ``XElement``              | Emits a *definition* template    |
| Light DOM        | ``CustomElement``         | No ``shadowroot`` / ``shadowdom``|
| Shadow DOM       | ``WebComponent``          | Requires ``shadowroot``/`shadowdom`|
| Alpine + X       | ``AlpineComponent``       | Needs ``x-data`` + ``x-tagname`` |
| Definition attr  | ``x-tagname="name"``      | Sole definition attribute        |
| Host tag         | ``<x-name>``              | Created by the browser runtime   |
| Browser runtime  | ``x_element.js``          | ``from ux_dom.scripts import …``  |
| Python helper    | ``x_element_js``          | Embeds / saves the runtime file  |
+------------------+---------------------------+----------------------------------+

Typical flow (one constructor = host)
--------------------------------------

1. Subclass ``CustomElement`` (light) or ``WebComponent`` (shadow).
2. Set ``tag_name`` on the **class** (or accept kebab-case class name).
3. ``render(tag_name)`` returns the **definition** template (built once per class).
4. **Construct the class to place a host** — never ``Instance()()``::

       Hello()                 # <x-hello>
       Hello(div("slot"))      # host with light-DOM children
       div(Hello(), Badge())   # many hosts; one definition each

5. Document auto-collects definitions from the class registry (single source of truth).
6. ``document.use(XElement())`` loads ``x_element.js``.

::

    from ux_dom.dom import div, template
    from ux_dom.dom.htmlelement import CustomElement

    class Hello(CustomElement):
        tag_name = "hello"

        def render(self, tag_name: str = "hello"):
            return template(div("Hi"), **{"x-tagname": tag_name})

    page = div(Hello(), Hello())   # organic — hosts only
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from ux_dom.dom.src import component
from ux_dom.dom.src.ext import DoubleTags
from ux_dom.dom.src.jinjatags import render_jinja
from ux_dom import diagnostics as _diag

__all__ = [
    "HTMLElement",
    "XTemplate",
    "AMPElement",
    "XElement",
    "CustomElement",
    "WebComponent",
    "AlpineElement",
    "AlpineComponent",
    "JinjaElement",
    "MarkdownElement",
    "ExampleCustomElement",
    "ExampleWebComponent",
]


# ---------------------------------------------------------------------------
# Plain HTML wrapper
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class HTMLElement(component.Component):
    """Thin Component that wraps arbitrary markup / paths without escaping.

    Prefer concrete tags (``div``, ``span``, …) for normal UI. Use this when
    you need a Component boundary around pre-built HTML or file content.
    """

    escape_string = False

    def __init__(self, *args, **kwargs):
        super(HTMLElement, self).__init__(*args, **kwargs)

    def __post_init__(self, *args, **kwargs):
        super(HTMLElement, self).__post_init__(*args, **kwargs)

    def render(self, elem_or_str_or_path):
        # Pass-through: no extra wrapping — caller owns the tree shape.
        return elem_or_str_or_path

    def __and__(self, other):
        return super().__and__(other)


# ---------------------------------------------------------------------------
# AMP (optional dialect)
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class AMPElement(component.Component):
    """Factory for ``amp-*`` tags (Accelerated Mobile Pages dialect).

    Not related to XElement. ``AMPElement("img")`` builds an ``amp-img`` tag
    class usable as ``AMPElement("img")(src=...)``.
    """

    tag_name: str

    def __post_init__(self, *args, **kwargs):
        super(AMPElement, self).__init__(*args, tag_name=self.tag_name, **kwargs)

        class Element(DoubleTags):
            tagname = f"amp-{self.tag_name}"  # noqa

        self.Element = Element
        self.Element.is_inline = self.is_inline
        self.Element.is_single = self.is_single
        self.Element.is_pretty = self.is_pretty

    def __call__(self, *args, **kwargs):
        return self.Element(*args, **kwargs)

    def __and__(self, other):
        return super().__and__(other)


# ---------------------------------------------------------------------------
# XElement registry — single source of truth for definitions
# ---------------------------------------------------------------------------


def _kebab_tag(name: str) -> str:
    """ClassName → class-name for default tag_name."""
    import re

    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1-\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s)
    return s.replace("_", "-").lower().strip("-")


class XElementRegistry:
    """One definition per element class / tag_name (process-wide).

    Authors never manage a definitions list. Hosts point at the registry entry;
    Document collects from hosts → registry definitions.
    """

    __slots__ = ("_by_class", "_by_tag")

    def __init__(self) -> None:
        self._by_class: dict = {}
        self._by_tag: dict = {}

    def get(self, cls):
        return self._by_class.get(cls)

    def get_tag(self, tag_name: str):
        return self._by_tag.get(str(tag_name))

    def put(self, cls, definition) -> None:
        tag = getattr(definition, "tag_name", None) or getattr(cls, "tag_name", None)
        self._by_class[cls] = definition
        if tag:
            self._by_tag[str(tag)] = definition

    def all_definitions(self):
        return list(self._by_class.values())

    def clear(self) -> None:
        """Test helper — not for production app code."""
        self._by_class.clear()
        self._by_tag.clear()


# Process-wide singleton — the only place definitions are owned
xelement_registry = XElementRegistry()


# ---------------------------------------------------------------------------
# XElement host tag (output of construction)
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class XTemplate(DoubleTags):
    """Host tag ``<x-{name}>`` — produced by constructing an XElement subclass.

    Prefer::

        Hello()                  # not Hello("hello")()
    """

    def __init__(self, *args, **kwargs):
        # File-backed definitions: load HTMLElement from filename=… (advanced).
        if getattr(self, "xelement", None) is None:
            parent_path = Path(sys.modules["__main__"].__file__).parent
            self.xelement = HTMLElement(parent_path / kwargs.pop("filename"))
            self.tagname = f"x-{self.xelement['x-tagname']}"
        super(XTemplate, self).__init__(*args, **kwargs)

    def __hash__(self) -> int:
        return super().__hash__()


# ---------------------------------------------------------------------------
# XElement — class defines once; construction places a host
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class XElement(component.Component):
    """Custom element type: **class = definition**, **instance call = host**.

    Single source of truth
    ----------------------
    The definition template for a subclass lives in :data:`xelement_registry`
    (one entry per class). You never pass definitions into the page by hand.

    Organic usage
    -------------
    ::

        class Hello(CustomElement):
            tag_name = "hello"          # optional; defaults to kebab class name

            def render(self, tag_name: str = "hello"):
                return template(div("Hi"), **{"x-tagname": tag_name})

        div(Hello(), Hello(span("x")))  # hosts only — no Hello()()

    ``render`` builds the **definition** (once per class). Constructing the
    class always returns a host ``<x-{tag_name}>``.
    """

    # Subclasses set ``tag_name = "hello"`` on the class body (plain class attr).
    tag_name = ""

    def __new__(cls, *args, **kwargs):
        # Internal: build the registry definition (Component instance).
        if kwargs.pop("__xelement_definition__", False):
            return super().__new__(cls)
        if cls is XElement:
            raise TypeError(
                "Subclass CustomElement or WebComponent; "
                "do not construct XElement() directly"
            )
        # Public: always a host. Definition is ensured first (single SSoT).
        definition = cls.definition()
        return definition.Template(*args, **kwargs)

    @classmethod
    def resolve_tag_name(cls) -> str:
        for klass in cls.__mro__:
            if klass is XElement:
                break
            raw = klass.__dict__.get("tag_name", None)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        return _kebab_tag(cls.__name__)

    @classmethod
    def definition(cls):
        """Return the sole definition instance for this class (registry SSoT)."""
        existing = xelement_registry.get(cls)
        if existing is not None:
            return existing
        tag = cls.resolve_tag_name()
        # Build definition Component without going through host __new__
        defn = cls.__new__(cls, __xelement_definition__=True)
        # dataclass / Component init as definition
        object.__setattr__(defn, "tag_name", tag)
        component.Component.__init__(defn, tag_name=tag)

        # Host factory bound to this definition
        class Template(XTemplate):
            tagname = f"x-{tag}"  # noqa
            xelement = defn

        defn.Template = Template
        defn.Template.is_inline = defn.is_inline
        defn.Template.is_single = defn.is_single
        defn.Template.is_pretty = defn.is_pretty
        xelement_registry.put(cls, defn)
        return defn

    def __post_init__(self, *args, **kwargs):
        # Only for definition instances built via definition() paths.
        if not getattr(self, "Template", None):
            tag = self.tag_name or type(self).resolve_tag_name()
            object.__setattr__(self, "tag_name", tag)
            if not getattr(self, "children", None) and not getattr(
                self, "_entry", None
            ):
                super(XElement, self).__init__(*args, tag_name=tag, **kwargs)

            class Template(XTemplate):
                tagname = f"x-{tag}"  # noqa
                xelement = self

            self.Template = Template
            self.Template.is_inline = self.is_inline
            self.Template.is_single = self.is_single
            self.Template.is_pretty = self.is_pretty
            xelement_registry.put(type(self), self)

    def __checks__(self, element):
        component.Component.__checks__(self, element)
        return self.__x_element_checks(element)

    def __x_element_checks(self, element):
        """Ensure the definition tree carries ``x-tagname``."""
        x_tagname_attr = None
        for key in ("x-tagname", "x_tagname"):
            try:
                x_tagname_attr = element[key]
                if x_tagname_attr:
                    break
            except (AttributeError, KeyError, TypeError):
                try:
                    x_tagname_attr = element.get(**{key: None})
                    if x_tagname_attr:
                        break
                except Exception:
                    pass

        if not x_tagname_attr:
            raise AttributeError(
                _diag.xelement_missing_tagname(
                    self.__class__.__name__, element.__class__.__qualname__
                )
            )
        return element

    def __call__(self, *args, **kwargs):
        """Return a host instance (same as constructing the class)."""
        return self.Template(*args, **kwargs)

    def __and__(self, other):
        return super().__and__(other)


# ---------------------------------------------------------------------------
# Light DOM — CustomElement
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class CustomElement(XElement):
    """Light-DOM custom element (no Shadow DOM).

    Use when styles/DOM should participate in the page tree (global CSS,
    easy HTMX swaps, simple composition).

    Rules
    -----
    * Must set ``x-tagname`` on the definition (inherited from XElement).
    * Must **not** set ``shadowroot`` or ``shadowdom`` (use WebComponent instead).

    Runtime (``x_element.js``)
    --------------------------
    Clones the ``<template>`` contents as **children of the host**
    (``host.append(template.content)``). No ``attachShadow``.

    See also
    --------
    * :class:`WebComponent` — isolated shadow tree + slots
    * ``examples/xelement_kit`` — full Light vs Shadow demos
    * ``docs/XELEMENT.md`` — guide
    """

    def __checks__(self, element):
        XElement.__checks__(self, element)
        return self.__custom_element_checks(element)

    def __custom_element_checks(self, element):  # noqa
        # Light DOM path: reject shadow attributes so authors pick the right base.
        try:
            shadow_root_attr = element["shadowroot"]
        except AttributeError:
            try:
                shadow_root_attr = element["shadowdom"]
            except AttributeError:
                shadow_root_attr = None

        if shadow_root_attr:
            raise AttributeError(
                _diag.xelement_light_with_shadow(
                    self.__class__.__name__, element.__class__.__qualname__
                )
            )
        return element


class ExampleCustomElement(CustomElement):
    """Minimal light-DOM sample — definition only.

    ::

        ExampleCustomElement("demo")      # <template x-tagname="demo"><div/></template>
        ExampleCustomElement("demo")()    # <x-demo></x-demo>
    """

    def render(self, tag_name):
        # Definition: template + x-tagname; body is what appears inside each host.
        with self.html_tags.template(**{"x-tagname": tag_name}) as cus_elem:
            self.html_tags.div()
        return cus_elem


# ---------------------------------------------------------------------------
# Shadow DOM — WebComponent
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class WebComponent(XElement):
    """Shadow-DOM custom element (encapsulated tree + optional slots).

    Use when you need style/DOM isolation, named slots, or closed roots.

    Rules
    -----
    * Must set ``x-tagname`` (XElement).
    * Must set ``shadowroot="true"|"open"`` or ``shadowdom="open"|"closed"``.

    Runtime (``x_element.js``)
    --------------------------
    Calls ``attachShadow({mode})`` and clones the template into the shadow
    root. Light-DOM children of the host project into ``<slot>``.

    See also
    --------
    * :class:`CustomElement` — light DOM
    * ``docs/XELEMENT.md``
    """

    def __checks__(self, element):
        XElement.__checks__(self, element)
        return self.__web_component_checks(element)

    def __web_component_checks(self, element):  # noqa
        # Prefer shadowroot=…; shadowdom=… is an accepted synonym.
        try:
            shadow_root_attr = element["shadowroot"]
        except AttributeError:
            shadow_root_attr = element.get(shadowroot=None)

        if not shadow_root_attr:
            try:
                shadow_root_attr = element["shadowdom"]
            except AttributeError:
                shadow_root_attr = element.get(shadowdom=None)

        if not shadow_root_attr:
            raise AttributeError(
                _diag.xelement_shadow_missing(
                    self.__class__.__name__, element.__class__.__qualname__
                )
            )
        return element


class ExampleWebComponent(WebComponent):
    """Minimal shadow-DOM sample with a default slot.

    ::

        ExampleWebComponent("card")                 # definition
        ExampleWebComponent("card")("light child")  # host with projection
    """

    def render(self, tag_name):
        # shadowroot="true" → open shadow root in x_element.js
        with self.html_tags.template(
            **{"x-tagname": tag_name}, shadowroot="true"
        ) as web_comp:
            self.html_tags.slot()
        return web_comp


# ---------------------------------------------------------------------------
# Alpine.js helpers
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class AlpineElement(component.Component):
    """Any component whose root must declare Alpine ``x-data``.

    Does **not** by itself register a custom element — combine with
    :class:`XElement` via :class:`AlpineComponent`.
    """

    def __checks__(self, element):
        return self.__alpine_js_checks(element)

    def __alpine_js_checks(self, element):
        # x-data may use any value; we only care that the attribute exists.
        try:
            x_data_attr = element["x-data"]
        except AttributeError:
            x_data_attr = element.get(x_data=None)

        if not x_data_attr:
            raise AttributeError(
                f"{self.__class__.__name__}.{element.__class__.__qualname__}: "
                f"must have 'x-data' attribute (Alpine.js)"
            )
        return element

    def __and__(self, other):
        return super().__and__(other)


@dataclass(eq=False)
class AlpineComponent(AlpineElement, XElement):
    """XElement + Alpine: requires ``x-tagname`` and ``x-data``.

    ``x_element.js`` clones the template then calls ``Alpine.initTree`` when
    Alpine is present on the page.
    """

    def __checks__(self, element):
        XElement.__checks__(self, element)
        return AlpineElement.__checks__(self, element)


# ---------------------------------------------------------------------------
# Template engines (unrelated to XElement custom elements)
# ---------------------------------------------------------------------------


class JinjaElement(component.Component):
    """Render a Jinja fragment via ``render_jinja`` when called with options."""

    escape_string = False

    def render(self, elem_or_str_or_path):
        return elem_or_str_or_path

    def __call__(self, **options):
        return render_jinja(self, **options)


class MarkdownElement(component.Component):
    """Component whose string children are treated as Markdown (when enabled)."""

    escape_string = False
    string_is_markdown = True

    def render(self, elem_or_str_or_path):
        return elem_or_str_or_path
