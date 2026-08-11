"""Dependency interoperability (valio + PEP 649).

Not a public API layer and not a legacy rename shim. Applied once at
``import ux_dom`` so optional valio fields work on modern annotation semantics.
Apps should not import this package.
"""
from .valio_pep649 import ensure_valio_pep649_compat

__all__ = ["ensure_valio_pep649_compat"]
