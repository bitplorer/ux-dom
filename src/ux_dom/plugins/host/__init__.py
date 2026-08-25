"""Host helpers — **not** the product path.

Product composition and delivery live in **ux-compose**.
``FastAPIHost`` is a fail-closed teaching stub.
"""

from ux_dom.plugins.host.fastapi import FastAPIHost, ProductHostMoved

__all__ = ["FastAPIHost", "ProductHostMoved"]
