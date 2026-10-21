# Copyright (c) 2022–2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""ux-dom — Python hypermedia **render** layer (tree → HTML / stream).

Brand lines
-----------
| Layer | Name |
|-------|------|
| **PyPI / pip** | ``ux-dom`` |
| **Import** | ``ux_dom`` |
| **CLI** | ``uxdom`` |

Ownership (residual-free)
-------------------------
**ux-dom renders.** Product delivery, host strategy, HMR process, and product
scaffold live in **ux-compose**.

| Layer | Package | Role |
|-------|---------|------|
| **Shell** | ``Document`` | HTML head/body SSoT — ``.use`` (control, runtime tags, CSP stamp) |
| **Core** | ``Component``, ``Fragment``, ``ReactiveComponent`` | Build trees |
| **DOM** | ``ux_dom.dom`` | Tags, parse, ``__render__`` / ``__async_render__`` |
| **UI kit** | ``ux_dom.ui`` | Optional copy-in components |

Serialize SSoT: ``tree.__render__()`` / ``tree.__async_render__()``.
Optional HTTP adapters under ``ux_dom.response`` are **not** the product path.

Product apps::

    uxcompose create-app myapp
    uxcompose build
    uxcompose serve dev app:asgi
    # composition root + CSS compile + delivery — see ux-compose FLOW:
    # https://github.com/bitplorer/ux-compose/blob/main/docs/FLOW.md

Pure document (no product host)::

    from ux_dom import Document, Component, XElement, Htmx, Csp
    from ux_dom.dom import div

    document = Document(head=[], body=[]).use(
        XElement(), Htmx(), Csp.auto()
    )

See ``docs/internals/SYSTEM.md`` and ux-compose FLOW:
https://github.com/bitplorer/ux-compose/blob/main/docs/FLOW.md
"""

from .settings import *  # Document  # isort: skip
from .slots import *  #Slots, WebComponentSlot, …  # isort: skip

from ux_dom.dom.src.component import (  # noqa: E402
    Component as Component,
    Fragment as Fragment,
    MergeClassAttribute as MergeClassAttribute,
    ReactiveComponent as ReactiveComponent,
)
# Document-facing facades: aliases over plugin implementations (no logic).
# ``Channel`` is the Document plugin, NOT ``ux_channel.Channel`` (action plane).
from ux_dom.plugins.control import HtmxControl as Htmx  # noqa: E402, F401
from ux_dom.plugins.csp import Csp as Csp  # noqa: E402
from ux_dom.plugins.runtime import UxChannelRuntime as Channel  # noqa: E402, F401
from ux_dom.plugins.runtime import XElementRuntime as XElement  # noqa: E402, F401

__version__ = "0.2.0"
