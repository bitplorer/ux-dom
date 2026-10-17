# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""Typed form field components (chars, integers, dates, ...). Optional helpers.

The only valio consumer in ux-dom, so the valio PEP 649 patch is applied here,
on first import of ``ux_dom.elements``, instead of on every ``import ux_dom``.
"""
from ._valio_pep649 import ensure_valio_pep649_compat

ensure_valio_pep649_compat()

# isort: split
from .booleans import *
from .buttons import *
from .chars import *
from .dates import *
from .enums import *
from .floats import *
from .integers import *
