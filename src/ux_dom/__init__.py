# Copyright (c) 2022–2026 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""ux-dom 0.1.0 — Python hypermedia UI (HTMX, Alpine, Web Components).

Brand lines
-----------
| Layer | Name |
|-------|------|
| **PyPI / pip** | ``ux-dom`` |
| **Import** | ``ux_dom`` |
| **CLI** | ``uxdom`` |

Ontology (public layers)
------------------------
| Layer | Package | Role |
|-------|---------|------|
| **Shell** | ``Document`` | HTML head/body SSoT, ``.use`` / ``.mount`` |
| **Core** | ``Component``, ``Fragment``, ``ReactiveComponent`` | Build & render trees |
| **DOM** | ``ux_dom.dom`` | Tags, parse, serialize |
| **Runtime** | ``ux_dom.runtime`` | ``XElement``, ``Htmx``, ``Csp``, ``Channel`` |
| **Plugins** | ``ux_dom.plugins`` | Host, routing, style, hub, contributions |
| **Routing** | ``ux_dom.routing`` | DirectoryRouter / StreamingRoute |
| **Response** | ``ux_dom.response`` | HTML / streaming adapters |
| **UI kit** | ``ux_dom.ui`` | Optional copy-in components |
| **CLI** | ``ux_dom.cli`` | create-app, doctor, build |

Quick start
-----------
::

    from fastapi import FastAPI
    from ux_dom import Document, Component
    from ux_dom.runtime import XElement, Htmx, Csp
    from ux_dom.dom import div

    document = Document(head=[], body=[]).use(
        XElement(), Htmx(), Csp.auto()
    )
    app = FastAPI(title="App")
    document.mount(app)

See ``docs/START_HERE.md``, ``docs/FEATURES.md``, and ``docs/internals/ARCHITECTURE.md``.
"""

from .compat.valio_pep649 import ensure_valio_pep649_compat

ensure_valio_pep649_compat()

from .settings import *  # Document, WebAssets, TailwindCommand, paths…  # isort: skip
from .slots import *  # Slots, WebComponentSlot, …  # isort: skip

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
