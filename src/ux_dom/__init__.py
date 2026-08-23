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
| **Discovery** | ``ux_dom.routing.core`` | Pure ``DirectoryRoutes`` + ``RouterHooks`` (host-free) |
| **UI kit** | ``ux_dom.ui`` | Optional copy-in components |

Serialize SSoT: ``tree.__render__()`` / ``tree.__async_render__()``.
Optional HTTP adapters under ``ux_dom.response`` are **not** the product path.

Product apps::

    uxcompose create-app myapp
    # composition root + delivery + HMR(dev) — see ux-compose docs/FLOW.md

Pure document (no product host)::

    from ux_dom import Document, Component
    from ux_dom.runtime import XElement, Htmx, Csp
    from ux_dom.dom import div

    document = Document(head=[], body=[]).use(
        XElement(), Htmx(), Csp.auto()
    )

See ``docs/internals/SYSTEM.md`` and ux-compose ``docs/FLOW.md``.
"""

from .compat.valio_pep649 import ensure_valio_pep649_compat

ensure_valio_pep649_compat()

from .settings import *  # Document, WebAssets, TailwindCommand, paths…  # isort: skip
from .slots import *  #Slots, WebComponentSlot, …  # isort: skip

from ux_dom.dom.src.component import (  # noqa: E402
    Component as Component,
    Fragment as Fragment,
    MergeClassAttribute as MergeClassAttribute,
    ReactiveComponent as ReactiveComponent,
)
from ux_dom.create import CreateProject as CreateProject  # noqa: E402
from ux_dom.runtime import (  # noqa: E402
    Channel as Channel,
    Csp as Csp,
    Htmx as Htmx,
    XElement as XElement,
)

__version__ = "0.1.0"
