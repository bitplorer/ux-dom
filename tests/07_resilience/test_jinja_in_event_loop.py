"""F5: Jinja export renders the same inside a running event loop."""

from __future__ import annotations

import asyncio

from ux_dom.dom import li
from ux_dom.dom.htmlelement import JinjaElement
from ux_dom.dom.src.jinjatags import _ENV, For, Var, render_jinja

XSS = "<img src=x onerror=alert(1)>"


def _render_all():
    return (
        str(render_jinja("{{ name }}!", name=XSS)),
        str(For("n in names", li(Var("n")))(names=["a", XSS])),
        str(JinjaElement(For("n in names", li(Var("n"))))(names=["b"])),
    )


def test_jinja_renders_inside_running_loop():
    expected = _render_all()

    async def main():
        return _render_all()

    assert asyncio.run(main()) == expected
    assert "&lt;img" in expected[0] and "<img" not in expected[0]


def test_jinja_env_stays_sandboxed_and_autoescaped():
    from jinja2.sandbox import SandboxedEnvironment

    assert isinstance(_ENV, SandboxedEnvironment)
    assert _ENV.autoescape is True
    assert _ENV.is_async is False
