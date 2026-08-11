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
