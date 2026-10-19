# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""Jinja control tags (For, If, Block, ...) as ux-dom nodes for template export.

Delimiter spacing is intentional; see tests for exact contracts.
"""
import threading

from jinja2.sandbox import SandboxedEnvironment

from ux_dom.dom.src.dom_tag import dom_tag
from ux_dom.dom.src.main import extension

__all__ = [
    "If",
    "Elif",
    "Else",
    "For",
    "AutoEscape",
    "Include",
    "Cycle",
    "Comment",
    "Extends",
    "Load",
    "CSRFToken",
    "Block",
    "Var",
    "render_jinja",
    "JinjaSingleTags",
    "JinjaDoubleTags",
    "JinjaBaseTag",
]


class JinjaBaseTag(object):
    pass


class JinjaDoubleTags(JinjaBaseTag, extension.DoubleTemplates):
    self_dedent = False
    child_dedent = False
    enable_left_delimiter_space = True
    enable_right_delimiter_space = True

    def __call__(self, **options):
        return render_jinja(self, **options)


class JinjaSingleTags(JinjaBaseTag, extension.SingleTemplates):
    self_dedent = False
    child_dedent = True
    enable_left_delimiter_space = True
    enable_right_delimiter_space = True

    def __call__(self, **options):
        return render_jinja(self, **options)


class Block(JinjaDoubleTags):
    def __init__(self, template_text, *dom_elements):
        """
        :param template_text:
        :param dom_elements: [optional] template
        """
        super(Block, self).__init__("block", template_text, *dom_elements)


class For(JinjaDoubleTags):
    def __init__(self, template_text, *dom_elements):
        """
        :param template_text:
        :param dom_elements: [optional] template
        """
        super(For, self).__init__("for", template_text, *dom_elements)


class If(JinjaDoubleTags):
    def __init__(self, template_text, *dom_elements):
        """
        :param template_text:
        :param dom_elements: [optional] template
        """
        super(If, self).__init__("if", template_text, *dom_elements)


class Elif(JinjaSingleTags):
    self_dedent = True
    child_dedent = False

    def __init__(self, template_text, *dom_elements):
        """
        :param template_text:
        :param dom_elements: [optional] template
        """

        super(Elif, self).__init__(
            "elif",
            template_text,
            *dom_elements,
        )


class Else(JinjaSingleTags):
    self_dedent = True
    child_dedent = False
    enable_right_delimiter_space = False

    def __init__(self, *dom_elements):
        """
        :param template_text:
        :param dom_elements: [optional] template
        """

        super(Else, self).__init__("else", "", *dom_elements)


class AutoEscape(JinjaSingleTags):
    def __init__(self, template_text, *dom_elements):
        """
        :param template_text:
        :param dom_elements: [optional] template
        """

        super(AutoEscape, self).__init__("autoescape", template_text, *dom_elements)


class Include(JinjaSingleTags):
    def __init__(self, template_text, *dom_elements):
        """
        :param template_text:
        :param dom_elements: [optional] template
        """

        super(Include, self).__init__("include", template_text, *dom_elements)


class Cycle(JinjaSingleTags):
    def __init__(self, template_text, *dom_elements):
        """
        :param template_text:
        :param dom_elements: [optional] template
        """

        super(Cycle, self).__init__("cycle", template_text, *dom_elements)


class Comment(JinjaDoubleTags):
    def __init__(self, template_text, *dom_elements):
        """
        :param template_text:
        :param dom_elements: [optional] template
        """

        super(Comment, self).__init__("comment", template_text, *dom_elements)


class Extends(JinjaSingleTags):
    def __init__(self, template_text, *dom_elements):
        """
        :param template_text:
        :param dom_elements: [optional] template
        """

        super(Extends, self).__init__("extends", template_text, *dom_elements)


class Load(JinjaSingleTags):
    def __init__(self, template_text, *dom_elements):
        """
        :param template_text:
        :param dom_elements: [optional] template
        """

        super(Load, self).__init__("load", template_text, *dom_elements)


class CSRFToken(JinjaSingleTags):
    def __init__(self, *dom_elements):
        """
        :param template_text:
        :param dom_elements: [optional] template
        """

        super(CSRFToken, self).__init__("csrf_token", "", *dom_elements)


class Var(JinjaSingleTags):
    left_delimiter = "{{"
    right_delimiter = "}}"

    def __init__(self, template_text, *dom_elements):
        """
        :param template_text:
        :param dom_elements: [optional] template
        """

        super(Var, self).__init__("", template_text, *dom_elements)


# Sandboxed, autoescaped environment: context values are text, and template
# code cannot reach Python internals.
_ENV = SandboxedEnvironment(
    autoescape=True, lstrip_blocks=True, trim_blocks=True, enable_async=True
)
# Braces in tree text and attribute strings are user data, not template code.
# They travel through Jinja as private-use characters and come back as entities.
# U+E000/U+E001/U+E002 already in the data are escaped first: the final swap
# must not rewrite user text or context values into &#123;/&#125;.
_LBRACE, _RBRACE, _ESC = "\ue000", "\ue001", "\ue002"
_EXPORT_LOCK = threading.RLock()


def _protect(text):
    return (
        text.replace(_ESC, _ESC + "0")
        .replace(_LBRACE, _ESC + "1")
        .replace(_RBRACE, _ESC + "2")
    )


def _hide_braces(text):
    return _protect(text).replace("{", _LBRACE).replace("}", _RBRACE)


def _needs_rewrite(text):
    return (
        "{" in text or "}" in text or _LBRACE in text or _RBRACE in text or _ESC in text
    )


def _finish(text):
    return (
        text.replace(_LBRACE, "&#123;")
        .replace(_RBRACE, "&#125;")
        .replace(_ESC + "1", _LBRACE)
        .replace(_ESC + "2", _RBRACE)
        .replace(_ESC + "0", _ESC)
    )


def _protect_context(value):
    """Escape sentinel characters in context values before render."""
    if isinstance(value, str):
        protected = _protect(value)
        if protected == value:
            return value
        if hasattr(value, "__html__") and not hasattr(protected, "__html__"):
            return value.__class__(protected)
        return protected
    if isinstance(value, dict):
        rebuilt = {}
        changed = False
        for key, item in value.items():
            new_key = _protect_context(key)
            new_item = _protect_context(item)
            rebuilt[new_key] = new_item
            if new_key is not key or new_item is not item:
                changed = True
        return rebuilt if changed else value
    if isinstance(value, (list, tuple)):
        rebuilt = tuple(_protect_context(item) for item in value)
        if all(a is b for a, b in zip(rebuilt, value, strict=True)):
            return value
        if isinstance(value, list):
            return list(rebuilt)
        try:
            return type(value)(rebuilt)
        except TypeError:
            return rebuilt
    return value


def _neutralize(node, undo):
    attrs = getattr(node, "attributes", None)
    if isinstance(attrs, dict):
        control = getattr(node, "CONTROL_ATTRS", ())
        for key, value in list(attrs.items()):
            if not isinstance(value, str) or not _needs_rewrite(value):
                continue
            # Control attributes are template syntax. Hide braces only in data.
            updated = _protect(value) if key in control else _hide_braces(value)
            if updated != value:
                undo.append((attrs, key, value))
                attrs[key] = updated
    if isinstance(node, dom_text):
        text = getattr(node, "text", None)
        if isinstance(text, str) and _needs_rewrite(text):
            # Missing `escaped` fails closed: the node is data, not template code.
            hide = getattr(node, "escaped", True)
            updated = _hide_braces(text) if hide else _protect(text)
            if updated != text:
                undo.append((node, "text", text))
                node.text = updated
        return
    children = getattr(node, "children", None)
    if not isinstance(children, list):
        return
    for i, child in enumerate(children):
        if isinstance(child, str):
            if _needs_rewrite(child):
                updated = type(child)(_hide_braces(child))
                if updated != child:
                    undo.append((children, i, child))
                    children[i] = updated
        else:
            _neutralize(child, undo)


def _restore(undo):
    for target, key, value in reversed(undo):
        if isinstance(target, (dict, list)):
            target[key] = value
        else:
            setattr(target, key, value)


def render_jinja(template, **options):
    safe_options = _protect_context(options)
    if isinstance(template, dom_tag):
        with _EXPORT_LOCK:
            undo = []
            try:
                _neutralize(template, undo)
                source = template.__render__()
            finally:
                _restore(undo)
    else:
        source = _protect(template) if isinstance(template, str) else template
    out = _ENV.from_string(source).render(**safe_options)
    return raw(_finish(out))


from ux_dom.dom.src.utils import dom_text, raw
