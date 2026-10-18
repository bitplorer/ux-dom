# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
# mypy: ignore-errors
# Re-export hub: html/svg both define ``title``; runtime prefers HTML via order.

"""HTML/SVG/Jinja tag surface for ux-dom.

Public import path for building trees::

    from ux_dom.dom import div, span, form, template, slot

See docs/internals/DESIGN_CANON.md and docs/guides/API_SURFACE.md.
"""
from .htmlelement import *  # isort: skip
from .htmldocument import *  # isort: skip

from .icons import *  # isort: skip
from .jinja import *  # isort: skip

from .src.component import *
from .src.csstags import *
from .src.ext import *
from .src.jinjatags import *
from .src.svgtags import *
from .src.htmltags import *  # HTML ``title`` last

from .src.utils import *  # isort: skip
from .src.dom_tag import *  # isort: skip

from .src.html_string import *  # isort: skip
from .uniqueid import *  # isort: skip

# Public seam (F-15): stable names for siblings — prefer these over ``ux_dom.dom.src.*``.
from .src.component import Component as Component
from .src.dom_tag import dom_tag as dom_tag
from .src.utils.dom_util import escape as escape, raw as raw


__all__ = [n for n in globals() if not n.startswith("_")]
# Prefer documenting the seam explicitly for importers and API snapshots:
for _n in ("Component", "dom_tag", "escape", "raw"):
    if _n not in __all__:
        __all__.append(_n)
