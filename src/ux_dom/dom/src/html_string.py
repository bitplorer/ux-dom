# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""Parse HTML strings into ux-dom nodes (defHTML) and related helpers.

Always strips runnable constructs (script/iframe/on*/Alpine/hx-on/javascript:
URLs, …). ``escape=True`` also HTML-escapes text nodes; ``escape=False`` keeps
text literal but still drops the runnable bits. ``raw()`` is the verbatim opt-out.
"""

import builtins
import types
import typing as T
from dataclasses import dataclass, field

from ux_dom.dom.src import ext, htmltags, jinjatags, svgtags
from ux_dom.dom.src.htmltags import html_tag
from ux_dom.dom.src.parse_html import Element, tokenize_html
from ux_dom.dom.src.utils import dom_text

__all__ = ["StringToHTML", "defHTML"]


# Cache dynamic tag classes so defHTML does not pollute ``__main__`` or
# re-create a new type for the same custom tag name on every parse.
_dynamic_element_registry: dict[str, T.Type[ext.Tags]] = {}


def create_dynamic_element(tag_name: str) -> T.Type[ext.Tags]:
    """Build (or reuse) a Tags subclass for unknown HTML/custom tag names.

    Previously this set attributes on ``sys.modules['__main__']`` and required
    ``__main__.__file__``, which polluted interactive sessions and crashed under
    some embedders. Classes are cached on a private registry instead.
    """
    if tag_name in _dynamic_element_registry:
        return _dynamic_element_registry[tag_name]

    cls_name = "".join(map(lambda x: x.capitalize(), tag_name.split("-"))) or "Dynamic"
    # Ensure a valid identifier
    if cls_name[0].isdigit():
        cls_name = "Tag" + cls_name

    class _Element(ext.Tags):
        tagname = tag_name

    _Element.__qualname__ = cls_name
    _Element.__name__ = cls_name
    _Element.__module__ = "ux_dom.dom.src.html_string"
    element: T.Type[ext.Tags] = _Element
    _dynamic_element_registry[tag_name] = element
    return element


# Tags / attrs always stripped on the string→markup path (defHTML / Fragment /
# Component / HTMLElement / JinjaElement / MarkdownElement). ``raw()`` is the
# only verbatim opt-out; it never goes through this parser.
_UNSAFE_TAGS = frozenset(
    {
        "script",
        "iframe",
        "object",
        "embed",
        "base",
        "link",
        "meta",
        "frame",
        "frameset",
        "applet",
        "style",
        "animate",
        "animatetransform",
        "animatemotion",
        "set",
        "foreignobject",
        "math",
        "maction",
    }
)

_URL_ATTRS = frozenset(
    {
        "href",
        "src",
        "xlink:href",
        "formaction",
        "action",
        "data",
        "poster",
        "cite",
        "background",
        "hx-get",
        "hx-post",
        "hx-put",
        "hx-patch",
        "hx-delete",
        "data-hx-get",
        "data-hx-post",
        "data-hx-put",
        "data-hx-patch",
        "data-hx-delete",
        "hx-sse",
        "hx-ws",
        "data-sse-connect",
        "data-ws-connect",
    }
)


def _norm_attr_name(key: str) -> str:
    """Match renderer: leading ``_`` is stripped (``_onclick`` → ``onclick``)."""
    k = str(key)
    while k.startswith("_"):
        k = k[1:]
    return k.lower()


def _scheme_is_dangerous(value: str) -> bool:
    # Strip C0/whitespace that browsers ignore before the scheme.
    cleaned = "".join(ch for ch in value if ch.isprintable() and not ch.isspace())
    low = cleaned.lower()
    for bad in ("javascript:", "vbscript:", "data:text/html"):
        if low.startswith(bad):
            return True
    return False


def _style_is_dangerous(value: str) -> bool:
    low = value.lower().replace("\\", "").replace("\0", "")
    return "javascript:" in low or "expression(" in low or "vbscript:" in low


def _attr_is_dangerous(key: str, value) -> bool:
    kl = _norm_attr_name(key)
    if kl.startswith("on"):
        return True
    # Alpine / Vue-style runtimes and htmx on* handlers.
    if kl.startswith("x-") or kl.startswith("x_"):
        return True
    if kl.startswith("@") or kl.startswith(":"):
        return True
    if kl.startswith("hx-on") or kl.startswith("data-hx-on"):
        return True
    if kl == "srcdoc":
        return True
    if not isinstance(value, str):
        return False
    if kl == "style" and _style_is_dangerous(value):
        return True
    if kl in _URL_ATTRS and _scheme_is_dangerous(value):
        return True
    return False


def _sanitize_attrs(attrs: dict) -> dict:
    """Drop event handlers, Alpine/htmx runtimes, and dangerous URLs."""
    if not attrs:
        return attrs
    out = {}
    for k, v in dict(attrs).items():
        if _attr_is_dangerous(k, v):
            continue
        out[k] = v
    return out


# Keep the old name as an alias so any external caller still resolves.
_UNSAFE_TAGS_WHEN_ESCAPE = _UNSAFE_TAGS
_sanitize_attrs_when_escape = _sanitize_attrs


@dataclass
class StringToHTML(object):
    # AST round-trip (HTML ↔ Python code object) is not implemented.
    # from https://stackoverflow.com/questions/68577587/how-to-find-the-ast-assignment-node-related-to-the-instance-creation
    # this.ast_object can be easily used to create python code for any html object
    # https://stackoverflow.com/a/68584740 for parsing a python object into an ast_object
    # https://stackoverflow.com/a/63212256 for unparsing a python ast_object

    html_string_or_token: T.Union[str, Element, list[Element], ext.Tags]
    modules: list[types.ModuleType] = field(default_factory=list)
    escape: bool = field(default=True)

    def __post_init__(self):
        self.tokens: T.Union[Element, list[Element], ext.Tags] = (
            tokenize_html(
                self.html_string_or_token
                if not isinstance(self.html_string_or_token, html_tag)
                else str(self.html_string_or_token)
            ).children
            if isinstance(self.html_string_or_token, (str, html_tag))
            else self.html_string_or_token
        )

        # for html, svg and jinja tags lookup
        if htmltags not in self.modules:
            self.modules.append(htmltags)

        if svgtags not in self.modules:
            self.modules.append(svgtags)

        if jinjatags not in self.modules:
            self.modules.append(jinjatags)

    def parse(self, tag: T.Optional[ext.Tags] = None) -> T.Union[str, ext.Tags, None]:
        for token in self.tokens:  # type: ignore[union-attr]
            if not token.name:
                # myst_parser gives out Data['abc'] kind of Token with {"name":'', 'data': 'abc', ...} attributes
                # we are parsing plain strings, <script> body or jinja token strings here

                if hasattr(token, "data"):
                    # handle leading and trailing newline with spaces in myst parser Data Token ex: "  \n Hello\n  "
                    if data := token.data.strip("\n").strip(" ").strip("\n"):
                        with tag or ext.PlaceholderTag() as tag:  # type: ignore[assignment]
                            # handling
                            if getattr(type(tag), "raw_text", None):
                                # <script>/<style> body: raw text element — never
                                # HTML-escaped; breakouts neutralized at render.
                                dom_text(data, escape=False)
                            else:
                                if token.__class__.__name__ != "Comment":
                                    # Braced text used to be emitted raw (Jinja
                                    # hole). Treat it as text; use the Jinja DSL
                                    # or raw() for real template fragments.
                                    dom_text(data, escape=self.escape)
                                else:
                                    # this is a comment section
                                    htmltags.comment(data)

            else:
                element = None
                tag_name = token.name
                if tag_name in builtins.__dict__:
                    # work around for builtins like 'input' tag
                    tag_name = "".join([token.name, "_"])

                for module in self.modules:
                    try:
                        element = getattr(module, tag_name)
                        if element is not None:
                            break
                    except (AttributeError,):
                        pass
                if element is None:
                    element = create_dynamic_element(tag_name=tag_name)

                # Always drop dangerous tags/attrs on the string→markup path.
                if str(token.name).lower() in _UNSAFE_TAGS:
                    continue

                attrs = _sanitize_attrs(dict(token.attrs or {}))

                # tag = tag if tag is not None else ConcatTag()

                if tag is not None:
                    with tag:
                        with element(**attrs) as child_tag:
                            StringToHTML(
                                token.children, modules=self.modules, escape=self.escape
                            ).parse(tag=child_tag)
                else:
                    with element(**attrs) as tag:
                        StringToHTML(
                            token.children, modules=self.modules, escape=self.escape
                        ).parse(tag=tag)
        return tag

    def __repr__(self):
        return str(self.parse())


# don't decorate defHTML with functools.lru_cache because if defHTML is used in isolation
# like:
# with div() as parent_div:
#   child_element = defHTML("some html string")
#
# with lru_cache decorated on defHTML the evaluation of child_element at run time will not happen twice
# and thus parent_div will never add child_element in subsequest runs thus better way to cache defHTML
# evaluation is to cache the method where it is used.
def defHTML(raw_string, escape=True) -> T.List[ext.Tags]:  # noqa
    if raw_string is None:
        return []
    if not isinstance(raw_string, str):
        raw_string = str(raw_string)
    tokens = tokenize_html(raw_string).children
    elements = []
    for token in tokens:
        element = StringToHTML([token], escape=escape).parse()
        if element:
            assert isinstance(
                element, ext.Tags
            ), f"{element=} is not instance of {ext.Tags}"
            elements.append(element)
    return elements


# if __name__ == '__main__':
# from ux_dom.dom import ConcatTag, For, Var, div, li, raw, script, ul

# print(defHTML("<li><ul><i><!--Hello World--></i></ul><a href='www.google.com'></a></li>"))
#     class XName(ext.Tags):
#         tagname = "x-name"


# print(defHTML(div("hello", div("Jai SHree Ram"), script(raw("function () => {}")), className="sdaf")).parse())
# print(div("hello", div("Jai SHree Ram"), script(raw("function () => {}")), className="sdaf"))
# print(defHTML(str(div("hello", div("Jai SHree Ram"), script(raw("function () => {}")), className="sdaf", x_data=None))))
# x = HTMLToPy(str(XName("hello", Var("haha"), ul(For("name in names", li(Var("name")))),
#                        div("Jai SHree Ram aa", className="safn"), script(raw("function () => {}")),
#                         script(src="https://unpkg.com/filepond/dist/filepond.js"),
#                         className="sdaf", x_data={}, x_transition_enter="")))
# print(x)
# print(XName("hello >", Var("haha >"), ul(For("name in names", li(Var("name")))),
#             div("Jai SHree Ram   a ", className="safn"), script(raw("function () => {}")),
#                         script(src="https://unpkg.com/filepond/dist/filepond.js"),
#                         className="sdaf", x_data={}, x_transition_enter=""))
# print(defHTML(str(ul(For("name in names", li(Var("name")))))))
