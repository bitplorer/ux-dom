# Copyright (c) 2023 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""Multi-slot WebComponent helper. Prefer WebComponent + slot() for new code."""
from dataclasses import dataclass, field

from ux_dom.dom.htmlelement import *
from ux_dom.dom.src.htmltags import *

__all__ = ["Slots"]


@dataclass(eq=False)
class Slots(WebComponent):
    """Declarative multi-slot shadow component.

    Parameters
    ----------
    slot_names:
        Named slots to emit (empty → single default ``<slot>``).
    classes:
        Optional ``part`` / class map keyed by tag_name or slot name.
    css:
        Stylesheet hrefs injected into the shadow tree.

    Uses ``x-tagname`` + ``shadowdom`` for ``x_element.js`` upgrade.
    Prefer plain ``WebComponent`` + ``slot()`` when you do not need this helper.
    """

    tag_name: str = "slots"
    slot_names: list[str] = field(default_factory=list)
    classes: dict = field(default_factory=dict)
    css: list[str] = field(default_factory=list)

    def __new__(cls, *args, **kwargs):
        kw = dict(kwargs)
        kw["__xelement_definition__"] = True
        return super().__new__(cls, *args, **kw)

    def __post_init__(self):
        super(Slots, self).__post_init__(
            slot_names=self.slot_names,
            classes=self.classes,
            css=self.css,
        )

    def render(self, tag_name, slot_names, classes, css):
        with template(**{"x-tagname": tag_name, "shadowroot": "true"}) as slots:
            # adding css files here...
            for css_href in css:
                link(href=css_href, rel="stylesheet", type="text/css")

            with div(
                className=classes.get(tag_name, False),
                part=tag_name,
                exportparts="*",
            ):
                if any(slot_names):
                    for name in slot_names:
                        with div(
                            part=name,
                            className=classes.get(name, False),
                            exportparts="*",
                        ):
                            slot(name=name)
                else:
                    slot()

        return slots

    def __call__(self, *args, **kwargs):
        return super(Slots, self).__call__(*args, exportparts="*", **kwargs)
