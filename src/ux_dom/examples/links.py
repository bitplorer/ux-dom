# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""Example snippet: links. Demo material under ux_dom.examples (not core API)."""
from ux_dom.dom.htmlelement import HTMLElement
from ux_dom.dom import a, div

__all__ = ["Link", "HtmxLink"]


class Link(HTMLElement):

    def render(self, *args, item_link, item_name=None, **kwargs):
        self.div = div() if item_name is None else div(item_name)
        return a(*args, self.div, href=item_link, **kwargs)


class HtmxLink(HTMLElement):

    def render(
        self, *args, item_link, target_id, item_name=None, push_url=True, **kwargs
    ):
        self.text = div() if item_name is None else div(item_name)
        link = div(
            *args,
            self.text,
            hx_get=item_link,
            hx_trigger="click",
            hx_target=target_id,
            className="cursor-pointer",
            **kwargs
        )
        if push_url:
            link["hx-push-url"] = "true"
        return link
