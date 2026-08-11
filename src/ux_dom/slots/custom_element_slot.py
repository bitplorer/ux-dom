# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""x_slot helper for named light-DOM slot projection into custom elements."""
from dataclasses import dataclass

from ux_dom.dom.htmlelement import *
from ux_dom.dom.src.htmltags import *

__all__ = ["SlotElement", "x_slot"]


@dataclass(eq=False)
class SlotElement(CustomElement):
    """Alpine-powered light-DOM slot factory (``x_slot`` instance).

    Definition-first helper (not host-first): used as a callable factory.
    """

    tag_name = "slot"

    def __new__(cls, *args, **kwargs):
        kw = dict(kwargs)
        kw["__xelement_definition__"] = True
        return super().__new__(cls, *args, **kw)

    def render(self, tag_name: str = "slot"):
        return template(
            div(
                template(
                    link(x_bind_href="ss", rel="stylesheet", type="text/css"),
                    x_for="ss in css",
                ),
                template(
                    div(
                        slot(x_bind_name="name"),
                        x_bind_part="name",
                        x_bind_class="classes[name]",
                        exportparts="*",
                    ),
                    x_for="name in slotnames",
                    tabindex=0,
                    x_if=" !!slotnames && slotnames.length && slotnames[0] !== '' ",
                ),
                template(
                    slot(),
                    tabindex=0,
                    x_if=" !slotnames || !slotnames.length || (slotnames.length && slotnames[0] == '') ",
                ),
                x_bind_class="classes[`${container_part}`]",
                x_bind_part="container_part",
                exportparts="*",
                x_data="{...slots(), ...$el.parentElement.data()}",
                x_cloak=None,
            ),
            script("""function slots(){
                return {
                    slotnames: [''],
                    classes:{}, 
                    css:[''] , 
                    container_part: ''
                        }
                    }"""),
            **{"x-tagname": tag_name},
        )


x_slot = SlotElement()

if __name__ == "__main__":
    print(x_slot.get(x_data=None))
