"""Plugin / Document errors must surface, not vanish (audit #59: B2, B3, B10)."""

# No ``from __future__ import annotations``: hooks below need real (eager-free,
# 3.14 deferred) annotations so signature inspection is exercised for real.
import enum
import functools
import typing as T

import pytest

from ux_dom.dom import div, script
from ux_dom.dom.src.component import Component
from ux_dom.plugins import App, PluginHub, XElementRuntime
from ux_dom.plugins.csp import stamp_nonce, stamp_tree
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


def test_typing_only_annotations_do_not_break_dispatch():
    if T.TYPE_CHECKING:  # pragma: no cover
        from ux_dom.plugins.hub import PluginHub as _TypingOnly  # noqa: F401
    calls = []

    def hook(ctx: _TypingOnly) -> _TypingOnly:  # noqa: F821
        calls.append("hook")
        return div("typed-hook")

    class RT:
        def mount(self, app: _TypingOnly) -> _TypingOnly:  # noqa: F821
            calls.append("mount")

    doc = Document(head=[hook], body=[]).use(RT())
    doc.mount(_Asgi())
    assert "typed-hook" in str(doc(div("x")))
    assert calls == ["mount", "hook"]


def _forwarding(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    return wrapper


def test_wraps_wrapped_hooks_use_wrapped_signature():
    @_forwarding
    def with_ctx(ctx):
        return div("ctx-ok" if "document" in ctx else "ctx-missing")

    @_forwarding
    def no_ctx():
        return div("no-ctx-ok")

    html = str(Document(head=[with_ctx, no_ctx], body=[])(div("x")))
    assert "ctx-ok" in html and "no-ctx-ok" in html


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


# ── B10: with no blanket except, the nonce walk must be robust by construction ─


class _Kind(enum.Enum):
    A = "a"


class _NamedInt(Component):
    name: int = 3

    def render(self):
        return div(script("x"))


class _NamedEnum(Component):
    name: _Kind = _Kind.A

    def render(self):
        return div(script("x"))


class _ChildrenMethod:
    def children(self):
        return [script("hidden")]


class _ChildrenInt:
    children = 5


@pytest.mark.parametrize(
    "node", [_NamedInt(), _NamedEnum(), _ChildrenMethod(), _ChildrenInt()]
)
@pytest.mark.parametrize("stamp", [stamp_tree, stamp_nonce])
def test_nonce_walk_tolerates_non_tag_attributes(stamp, node):
    s = script("ok")
    stamp([node, div(s)], "N")
    assert s.attributes.get("nonce") == "N"


def test_nonce_walk_still_stamps_script_named_by_tagname():
    s = script("x")
    stamp_tree(div(div(s)), "N", tags=("script",))
    assert s.attributes.get("nonce") == "N"


def test_nonce_walk_propagates_genuine_errors():
    class Exploding:
        @property
        def children(self):
            raise RuntimeError("broken node")

    with pytest.raises(RuntimeError, match="broken node"):
        stamp_tree(Exploding(), "N")
