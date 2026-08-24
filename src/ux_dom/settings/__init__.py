# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

"""Document + fail-closed product stubs.

``WebAssets`` and ``TailwindCommand`` raise teaching errors.
App layout: ``from ux_compose import WebAssets``.
Product CSS: ``uxcompose build``.
"""
from .document import *

from .commands import ProductCssMoved as ProductCssMoved  # isort: skip
from .commands import TailwindCommand as TailwindCommand  # isort: skip
