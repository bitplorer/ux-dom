"""Plugin / Document errors must surface, not vanish (audit #59: B2, B3, B10)."""

from __future__ import annotations

import pytest

from ux_dom.dom import div
from ux_dom.plugins import App, PluginHub, XElementRuntime
from ux_dom.settings.document import Document


class _Asgi:
    """Minimal ASGI-shaped host (no routes needed)."""


# ── B2: App.build must not swallow Document.mount ─────────────────────────


def test_app_build_propagates_document_mount_error():
    class BoomDoc(Document):
        def mount(self, app):
            raise RuntimeError("middleware misconfigured")

    with pytest.raises(RuntimeError, match="middleware misconfigured"):
        App(document=BoomDoc(head=[], body=[])).build(asgi=_Asgi())


# ── B3: no TypeError retry (one call, inner error surfaces) ───────────────


def test_runtime_mount_called_once_and_inner_typeerror_surfaces():
    calls = []

    class RT:
        def mount(self, app, hub=None):
            calls.append(hub)
            raise TypeError("body bug")

    doc = Document(head=[], body=[]).use(RT())
    with pytest.raises(TypeError, match="^body bug$"):
        doc.mount(_Asgi())
    assert len(calls) == 1


def test_runtime_mount_requiring_hub_gets_hub_none():
    calls = []

    class RT:
        def mount(self, app, *, hub):
            calls.append(hub)

    Document(head=[], body=[]).use(RT()).mount(_Asgi())
    assert calls == [None]


def test_stage_hook_inner_typeerror_surfaces_once():
    calls = []

    def hook(ctx):
        calls.append(ctx)
        raise TypeError("body bug")

    with pytest.raises(TypeError, match="^body bug$"):
        str(Document(head=[hook], body=[])(div("x")))
    assert len(calls) == 1


def test_stage_hook_without_ctx_still_called():
    html = str(Document(head=[lambda: div("no-ctx")], body=[])(div("x")))
    assert "no-ctx" in html


# ── B10: hub contribution errors must not drop runtime tags silently ──────


def test_hub_contribution_error_propagates_from_render():
    class Bad:
        name = "bad"
        plugin_kind = "contribution"

        def artifacts(self):
            return ()

        def document_head(self):
            raise KeyError("config missing")

        def document_body(self):
            return ()

    hub = PluginHub()
    hub.add_contribution(XElementRuntime())
    hub.add_contribution(Bad())
    doc = Document(head=[], body=[], include_runtimes=True, hub=hub)
    with pytest.raises(KeyError, match="config missing"):
        str(doc(div("x")))
