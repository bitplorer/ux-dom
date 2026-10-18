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
_LBRACE, _RBRACE = "\ue000", "\ue001"
_EXPORT_LOCK = threading.RLock()


def _hide_braces(text):
    return text.replace("{", _LBRACE).replace("}", _RBRACE)


def _neutralize(node, undo):
    attrs = getattr(node, "attributes", None)
    if isinstance(attrs, dict):
        control = getattr(node, "CONTROL_ATTRS", ())
        for key, value in list(attrs.items()):
            if key in control:
                continue
            if isinstance(value, str) and ("{" in value or "}" in value):
                undo.append((attrs, key, value))
                attrs[key] = _hide_braces(value)
    if isinstance(node, dom_text):
        if getattr(node, "escaped", False) and ("{" in node.text or "}" in node.text):
            undo.append((node, "text", node.text))
            node.text = _hide_braces(node.text)
        return
    children = getattr(node, "children", None)
    if not isinstance(children, list):
        return
    for i, child in enumerate(children):
        if isinstance(child, str):
            if "{" in child or "}" in child:
                undo.append((children, i, child))
                children[i] = type(child)(_hide_braces(child))
        else:
            _neutralize(child, undo)


def _restore(undo):
    for target, key, value in reversed(undo):
        if isinstance(target, (dict, list)):
            target[key] = value
        else:
            setattr(target, key, value)


def render_jinja(template, **options):
    if isinstance(template, dom_tag):
        with _EXPORT_LOCK:
            undo = []
            try:
                _neutralize(template, undo)
                source = template.__render__()
            finally:
                _restore(undo)
    else:
        source = template
    out = _ENV.from_string(source).render(**options)
    return raw(out.replace(_LBRACE, "&#123;").replace(_RBRACE, "&#125;"))


from ux_dom.dom.src.utils import dom_text, raw
