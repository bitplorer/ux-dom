"""F-07: Document.mount must not swallow static-install failures."""

from __future__ import annotations

from pathlib import Path

import pytest

from ux_dom.plugins.safe_static import SafeStaticFile, install_safe_static
from ux_dom.settings.document import Document


class _NoRoutes:
    """ASGI-shaped object without add_route / add_api_route."""


def _fake_file():
    # path must exist for some checks — use this file
    here = Path(__file__).resolve()
    return SafeStaticFile(
        url="/ux-dom/static/x_element.js",
        path=here,
        package_root=here.parent,
        content_type="application/javascript",
        plugin="test",
    )


def test_install_safe_static_returns_0_on_no_route_api():
    assert install_safe_static(_NoRoutes(), [_fake_file()]) == 0


def test_document_mount_raises_when_static_cannot_install():
    class RT:
        def served_files(self):
            return [_fake_file()]

        def mount(self, app, hub=None):
            return None

    doc = Document(head=[], body=[]).use(RT())
    with pytest.raises(RuntimeError, match="install_safe_static installed 0"):
        doc.mount(_NoRoutes())


def test_document_mount_ok_when_routes_exist(tmp_path):
    class App:
        def __init__(self):
            self.routes = []

        def add_api_route(self, url, handler, **kw):
            self.routes.append(url)

    here = Path(__file__).resolve()
    sf = SafeStaticFile(
        url="/ux-dom/static/x.js",
        path=here,
        package_root=here.parent,
        content_type="application/javascript",
        plugin="t",
    )

    class RT:
        def served_files(self):
            return [sf]

        def mount(self, app, hub=None):
            return None

    app = App()
    Document(head=[], body=[]).use(RT()).mount(app)
    assert app.routes == ["/ux-dom/static/x.js"]
