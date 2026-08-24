# Copyright (c) 2026 ux-dom
"""Legacy helpers — **not** the product scaffold path.

Product applications: ``uxcompose create-app`` (ux-compose).

``CreateProject.write()`` and ``CreateAsgi.build()`` fail closed with a
teaching error.
"""

from ux_dom.create.asgi import CreateAsgi, ProductAsgiMoved
from ux_dom.create.project import CreateProject, ProductScaffoldMoved

__all__ = [
    "CreateAsgi",
    "CreateProject",
    "ProductAsgiMoved",
    "ProductScaffoldMoved",
]
