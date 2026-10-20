"""F-07: Document.mount must not swallow static-install failures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ux_dom.plugins.safe_static import SafeStaticFile, install_safe_static
from ux_dom.settings.document import Document

_HERE = Path(__file__).resolve()


class _NoRoutes:
    """ASGI-shaped object without add_route / add_api_route."""


class _ApiRoutes:
    """Minimal FastAPI-shaped app that records add_api_route calls."""

    def __init__(self):
        self.routes = []

    def add_api_route(self, url, handler, **kw):
        self.routes.append(url)


def _file(url="/ux-dom/static/x_element.js", path=_HERE):
    # Route registration does not read the file; serving/collecting re-validates
    # it (allowlisted extension, under package_root), so those tests pass a .js.
    return SafeStaticFile(
        url=url,
        path=path,
        package_root=path.parent,
        content_type="application/javascript",
        plugin="test",
    )


def _runtime(*files):
    class RT:
        def served_files(self):
            return list(files)

        def mount(self, app, hub=None):
            return None

    return RT()


def test_install_safe_static_returns_0_on_no_route_api():
    assert install_safe_static(_NoRoutes(), [_file()]) == 0


def test_document_mount_raises_when_static_cannot_install():
    doc = Document(head=[], body=[]).use(_runtime(_file()))
    with pytest.raises(RuntimeError, match="install_safe_static installed 0"):
        doc.mount(_NoRoutes())


def test_document_mount_ok_when_routes_exist():
    app = _ApiRoutes()
    Document(head=[], body=[]).use(_runtime(_file("/ux-dom/static/x.js"))).mount(app)
    assert app.routes == ["/ux-dom/static/x.js"]


def test_mount_names_starlette_when_it_is_missing(monkeypatch):
    for mod in ("starlette", "starlette.responses", "fastapi", "fastapi.responses"):
        monkeypatch.setitem(sys.modules, mod, None)
    doc = Document(head=[], body=[]).use(_runtime(_file()))
    with pytest.raises(RuntimeError, match="starlette is required") as ei:
        doc.mount(_ApiRoutes())
    assert "add_api_route/add_route" not in str(ei.value)


def test_install_safe_static_raises_on_first_failing_route():
    class Flaky(_ApiRoutes):
        def add_api_route(self, url, handler, **kw):
            if url.endswith("b.js"):
                raise ValueError("boom")
            super().add_api_route(url, handler, **kw)

    app = Flaky()
    files = [_file(f"/ux-dom/static/{n}.js") for n in ("a", "b", "c")]
    with pytest.raises(RuntimeError) as ei:
        install_safe_static(app, files)
    assert "/ux-dom/static/b.js" in str(ei.value)
    assert isinstance(ei.value.__cause__, ValueError)
    # first-failure semantics: earlier routes stay, later ones are skipped
    assert app.routes == ["/ux-dom/static/a.js"]


def _js(tmp_path):
    js = tmp_path / "x.js"
    js.write_text("console.log(1);\n")
    return js


def test_plain_starlette_add_route_serves_200(tmp_path):
    pytest.importorskip("httpx")
    from starlette.applications import Starlette
    from starlette.testclient import TestClient

    js = _js(tmp_path)
    app = Starlette()
    rt = _runtime(_file("/ux-dom/static/x.js", js))
    Document(head=[], body=[]).use(rt).mount(app)
    resp = TestClient(app).get("/ux-dom/static/x.js")
    assert resp.status_code == 200
    assert resp.content == js.read_bytes()


def test_hub_static_path_raises_when_0_of_n_installed(tmp_path):
    from ux_dom.plugins.hub import PluginHub, _mount_package_static

    js = _js(tmp_path)

    class Hub(PluginHub):
        def iter_contributions(self):
            return [_runtime(_file(path=js))]

    with pytest.raises(RuntimeError, match="installed 0 of 1"):
        _mount_package_static(_NoRoutes(), Hub())
