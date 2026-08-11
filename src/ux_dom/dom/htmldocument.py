# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""HTML document shell — two-stage head/body placement + auto XElement defs.

Stage order (``render``)::

    <head>
      [B] call-time head     (page title, page CSS)
      [A] common_head        (shared meta, XElement runtime, …)
    </head>
    <body>
      content (*args)
      [B] call-time body
      Body placeholder
      XElement definitions slot  (auto-filled at pre_render)
      [A] common_body            (HTMX, …)
    </body>

Authors place **hosts** only; ``_collect_xelement_definitions`` dedupes
definition templates into the definitions slot (see XELEMENT_AUTO_DEFINITIONS).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ux_dom.dom.htmlelement import XTemplate
from ux_dom.dom.src import component
from ux_dom.dom.src.dom_tag import dom_tag
from ux_dom.dom.src.main import extension

__all__ = ["HtmlDocument"]


class Head(component.Component):
    def render(self, *args, **kwargs):
        self.add(kwargs)
        self.add(*args)
        return self


class Body(component.Component):
    def render(self, *args, **kwargs):
        self.add(kwargs)
        self.add(*args)
        return self


@dataclass(eq=False)
class HtmlDocument(component.Component):
    csrf_field = "X-CSRF-TOKEN"
    ensure_csrf_token: bool = field(default=True, init=False)

    def __init__(self, *args, **kwargs):
        self.ensure_csrf_token = kwargs.pop("ensure_csrf_token", self.ensure_csrf_token)
        self.document = self
        super(HtmlDocument, self).__init__(*args, **kwargs)
        self._entry = self.body
        self._old_entry = None

    def __pre_render__(self, *args, **kwargs):
        # Auto definitions: hosts in the page → one <template x-tagname> each
        # under _xelemet_placeholder (no manual definitions list).
        self._collect_xelement_definitions(self.body)
        if title := self.body.get("title"):
            title = title[0]
            title_parent: dom_tag = title.parent
            if title_parent is not None:
                title_parent.remove(title)
                self.head.add(title)

        if not self.head.get("meta", charset="utf-8"):
            charset = self.html_tags.meta(charset="utf-8")
            self.head.add(charset)

        if not self.head.get("meta", name="viewport"):
            viewport_meta = self.html_tags.meta(
                name="viewport",
                content=(
                    "width=device-width, initial-scale=1, maximum-scale=1, "
                    "user-scalable=no, minimal-ui"
                ),
            )
            self.head.add(viewport_meta)

    def __enter__(self):
        super().__enter__()
        self._old_entry = self._entry
        self._entry = self._entry_with_context
        return self

    def __exit__(self, type, value, traceback):
        super().__exit__(type, value, traceback)
        self._entry = self._old_entry

    def _may_shift_Head_to_head(self):
        if head_node_list := self.body.get(tag=Head):
            if head_node_list:
                for head_node in head_node_list:
                    head_parent: dom_tag = head_node.parent
                    if head_parent is not None:
                        if head_parent is self.head:
                            continue
                        head_parent.remove(head_node)
                        self.head.add(head_node)

    def _may_shift_Body_to_body(self):
        if body_node_list := self.body.get(tag=Body):
            if body_node_list:
                for body_node in body_node_list:
                    body_parent: dom_tag = body_node.parent
                    if body_parent is not None:
                        if body_parent is self._Body_placeholder:
                            continue
                        body_parent.remove(body_node)
                        self._Body_placeholder.add(body_node)

    def _definition_tag_name(self, node: dom_tag):
        """Return ``x-tagname`` / ``tag_name`` for a definition node, if any."""
        if node is None:
            return None
        for key in ("x-tagname", "x_tagname"):
            try:
                val = node[key]
                if val:
                    return str(val)
            except (AttributeError, KeyError, TypeError):
                pass
            try:
                attrs = getattr(node, "attributes", None) or {}
                if key in attrs and attrs[key]:
                    return str(attrs[key])
                ck = key.replace("-", "_")
                if ck in attrs and attrs[ck]:
                    return str(attrs[ck])
            except (AttributeError, TypeError):
                pass
        tag_name = getattr(node, "tag_name", None)
        if tag_name:
            return str(tag_name)
        entry = getattr(node, "_entry", None)
        if entry is not None and entry is not node:
            return self._definition_tag_name(entry)
        return None

    def _is_under_definitions_slot(self, node: dom_tag) -> bool:
        cur: object | None = node
        guard = 0
        while cur is not None and guard < 64:
            if cur is getattr(self, "_xelemet_placeholder", None):
                return True
            cur = getattr(cur, "parent", None)
            guard += 1
        return False

    def _register_definition(self, definition, seen: set) -> None:
        """Ensure one definition per ``x-tagname`` under the definitions slot."""
        if definition is None:
            return
        tag = self._definition_tag_name(definition)
        if not tag or tag in seen:
            return
        if self._is_under_definitions_slot(definition):
            seen.add(tag)
            return
        seen.add(tag)
        parent = getattr(definition, "parent", None)
        if parent is not None:
            try:
                parent.remove(definition)
            except Exception:
                pass
        self._xelemet_placeholder.add(definition)

    def _collect_xelement_definitions(self, search_element: dom_tag) -> None:
        """Auto-collect custom-element definitions from the live tree.

        Intent (original ux-dom): authors place **hosts** only; Document pulls
        every linked definition into a single slot, **deduped by x-tagname**,
        so large pages never manually maintain a definitions list.
        """
        if search_element is None:
            return
        seen: set = set()
        # Walk hosts: XTemplate nodes carry .xelement → definition
        try:
            templates = search_element.get(XTemplate) or []
        except (AttributeError, TypeError):
            templates = []
        for xt in templates:
            defn = getattr(xt, "xelement", None)
            if defn is not None:
                self._register_definition(defn, seen)
        # Also walk nodes that are definition templates themselves (x-tagname)
        try:
            stack = list(getattr(search_element, "children", None) or [])
        except Exception:
            stack = []
        guard = 0
        while stack and guard < 10000:
            guard += 1
            node = stack.pop()
            if not isinstance(node, dom_tag):
                continue
            if self._definition_tag_name(node) and not getattr(node, "xelement", None):
                # likely a definition template root
                if node is not search_element:
                    self._register_definition(node, seen)
            try:
                stack.extend(list(getattr(node, "children", None) or []))
            except Exception:
                pass

    def __checks__(self, element):
        if self.ensure_csrf_token:
            token_element = element.get(name=self.csrf_field)
            if not token_element:
                raise AttributeError(
                    f"{self.__class__.__qualname__} {self.csrf_field} must be set"
                )
            if len(token_element) > 1:
                raise AssertionError(
                    f"{self.__class__.__qualname__} {self.csrf_field} set at multiple places"
                )
        return element

    def render(
        self, *args, head=None, body=None, common_head=None, common_body=None, **kwargs
    ):
        common_head = (
            [common_head] if not isinstance(common_head, list) else common_head
        )
        common_body = (
            [common_body] if not isinstance(common_body, list) else common_body
        )
        head = [head] if not isinstance(head, list) else head
        body = [body] if not isinstance(body, list) else body

        doc = self.html_tags.DocType("html")
        with self.html_tags.html() as self.html:
            # ^Head Section
            with self.html_tags.head() as self.head:
                if any(head):
                    for _head_file in head:
                        if isinstance(_head_file, dom_tag):
                            self.head.add(_head_file)
                        elif isinstance(_head_file, str):
                            if str(_head_file).rstrip("/").endswith((".js", ".mjs")):
                                self.head.add(self.html_tags.script(src=_head_file))
                            else:
                                self.head.add(
                                    self.html_tags.link(
                                        href=_head_file, rel="stylesheet"
                                    )
                                )
                        elif isinstance(_head_file, dict):
                            d = dict(_head_file)
                            tag = d.pop("tag", None)
                            if tag in ("script", "js") or (
                                "src" in d and "href" not in d
                            ):
                                self.head.add(self.html_tags.script(**d))
                            elif tag == "meta" or (
                                "charset" in d or "name" in d or "http_equiv" in d
                            ):
                                self.head.add(self.html_tags.meta(**d))
                            else:
                                d.setdefault("rel", "stylesheet")
                                self.head.add(self.html_tags.link(**d))

                if any(common_head):
                    for _hd in common_head:
                        if isinstance(_hd, dom_tag):
                            self.head.add(_hd)

            # ^Body Section
            self._entry_with_context = extension.PlaceholderTag()
            self._Body_placeholder = extension.PlaceholderTag()
            self._xelemet_placeholder = extension.PlaceholderTag()
            with self.html_tags.body(
                self._entry_with_context, *args, **kwargs
            ) as self.body:
                if any(body):
                    for _body_file in body:
                        if isinstance(_body_file, dom_tag):
                            self.body.add(_body_file)
                        elif isinstance(_body_file, str):
                            if str(_body_file).rstrip("/").endswith(".css"):
                                self.body.add(
                                    self.html_tags.link(
                                        href=_body_file, rel="stylesheet"
                                    )
                                )
                            else:
                                self.body.add(self.html_tags.script(src=_body_file))
                        elif isinstance(_body_file, dict):
                            d = dict(_body_file)
                            tag = d.pop("tag", None)
                            if tag in ("link", "css") or (
                                "href" in d and "src" not in d
                            ):
                                d.setdefault("rel", "stylesheet")
                                self.body.add(self.html_tags.link(**d))
                            else:
                                self.body.add(self.html_tags.script(**d))

                self.body.add(self._Body_placeholder)
                # Definitions slot: auto-filled at pre_render from hosts
                self.body.add(self._xelemet_placeholder)

                if any(common_body):
                    for _bd in common_body:
                        if isinstance(_bd, dom_tag):
                            self.body.add(_bd)

        return doc, self.html

    def _walk_render_tokens(self, indent_level, indent_str, pretty, xhtml, _seen=None):
        """Token walk with pre_render once — pretty path must not double-run it.

        Compact (pretty=False) runs ``__pre_render__`` here then streams tokens.
        Pretty delegates to ``_render`` which also calls ``__pre_render__`` —
        so we skip the extra call when pretty is active.
        """
        pretty_flag = pretty and self.is_pretty and not self.is_inline
        if not pretty_flag:
            self.__pre_render__()
        return super()._walk_render_tokens(
            indent_level, indent_str, pretty, xhtml, _seen=_seen
        )

    def _render(
        self, sb, indent_level=1, indent_str="  ", pretty=True, xhtml=False, _seen=None
    ):
        self.__pre_render__()
        return super()._render(sb, indent_level, indent_str, pretty, xhtml, _seen=_seen)
