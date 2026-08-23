# Copyright (c) 2026 ux-dom
"""Legacy helpers — **not** the product scaffold path.

Product applications: ``uxcompose create-app`` (ux-compose).

``CreateProject.write()`` fails closed with a teaching error.
``CreateAsgi`` remains for tests and pure-dom scripts only.
"""

from ux_dom.create.asgi import CreateAsgi
from ux_dom.create.project import CreateProject, ProductScaffoldMoved

__all__ = ["CreateAsgi", "CreateProject", "ProductScaffoldMoved"]
