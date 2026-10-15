# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Import-time deprecation notice for ``ux_dom.dom.ui``.

Imported first by that module so the warning is emitted before optional
third-party imports (tortoise) run.
"""

import warnings

warnings.warn(
    "ux_dom.dom.ui is a deprecated Tortoise form helper.",
    DeprecationWarning,
    stacklevel=3,
)
