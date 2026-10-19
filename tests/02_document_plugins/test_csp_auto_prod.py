"""F-06: Csp.auto unset DEBUG is prod; prod has no unsafe-inline / bare ws:."""

from __future__ import annotations

import pytest

from ux_dom.plugins.csp import Csp, build_csp_header, policy_prod


def test_auto_unset_debug_is_prod(monkeypatch):
    monkeypatch.delenv("DEBUG", raising=False)
    c = Csp.auto()
    assert list(c.script_hosts) == []
    assert c.script_unsafe_inline_legacy is False
    assert "ws:" not in list(c.connect_src)
    assert "wss:" not in list(c.connect_src)


def test_auto_debug_1_is_dev(monkeypatch):
    monkeypatch.setenv("DEBUG", "1")
    c = Csp.auto()
    assert c.style_unsafe_inline is True
    assert list(c.script_hosts)  # CDN hosts


def test_prod_header_has_no_unsafe_inline_or_bare_ws():
    h = build_csp_header("N", **Csp.prod().to_policy().header_kwargs())
    # script-src must not carry 'unsafe-inline'
    script = [p for p in h.split(";") if "script-src" in p][0]
    assert "'unsafe-inline'" not in script
    assert "ws:" not in h and "wss:" not in h
    assert "connect-src 'self'" in h or "connect-src 'self';" in h.replace("  ", " ")


def test_policy_prod_knobs():
    p = policy_prod()
    assert p.script_unsafe_inline_legacy is False
    assert p.connect_src == ("'self'",)


@pytest.mark.parametrize(
    "val",
    ("0", "false", "False", "", "FALSE", "no", "off", "n", " 0", "0 "),
)
def test_auto_debug_false_strings_are_prod(monkeypatch, val):
    monkeypatch.setenv("DEBUG", val)
    c = Csp.auto()
    assert list(c.script_hosts) == [], val
    assert c.script_unsafe_inline_legacy is False, val


@pytest.mark.parametrize("val", ("1", "true", " TRUE ", "yes", "on"))
def test_auto_debug_truthy_strings_are_dev(monkeypatch, val):
    monkeypatch.setenv("DEBUG", val)
    c = Csp.auto()
    assert c.style_unsafe_inline is True, val
    assert list(c.script_hosts), val
