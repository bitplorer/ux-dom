"""F-09: valio PEP 649 patch marks applied only on success; failures raise."""

from __future__ import annotations

import sys

import pytest


def test_ensure_raises_and_leaves_unapplied_on_hook_failure(monkeypatch):
    from ux_dom.compat import valio_pep649 as v

    monkeypatch.setattr(v, "_APPLIED", False)
    monkeypatch.setattr(
        v,
        "_install_safe_hooks",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("hook boom")),
    )
    for k in list(sys.modules):
        if k == "valio" or k.startswith("valio."):
            del sys.modules[k]

    with pytest.raises(RuntimeError, match="hook boom"):
        v.ensure_valio_pep649_compat()
    assert v._APPLIED is False


def test_ensure_succeeds_and_marks_applied(monkeypatch):
    from ux_dom.compat import valio_pep649 as v

    monkeypatch.setattr(v, "_APPLIED", False)
    for k in list(sys.modules):
        if k == "valio" or k.startswith("valio."):
            del sys.modules[k]
    v.ensure_valio_pep649_compat()
    assert v._APPLIED is True
    import valio

    assert hasattr(valio, "Validator")
    # Idempotent: a subsequent call must not re-enter the install path.
    calls = {"n": 0}
    real = v._install_safe_hooks

    def counting(*a, **k):
        calls["n"] += 1
        return real(*a, **k)

    monkeypatch.setattr(v, "_install_safe_hooks", counting)
    v.ensure_valio_pep649_compat()
    assert calls["n"] == 0
    assert v._APPLIED is True


def test_missing_valio_dist_raises(monkeypatch):
    from ux_dom.compat import valio_pep649 as v
    import importlib.metadata as md

    monkeypatch.setattr(v, "_APPLIED", False)
    for k in list(sys.modules):
        if k == "valio" or k.startswith("valio."):
            del sys.modules[k]

    def boom(name):
        raise md.PackageNotFoundError(name)

    monkeypatch.setattr(md, "distribution", boom)
    with pytest.raises(RuntimeError, match="requires the valio"):
        v.ensure_valio_pep649_compat()
    assert v._APPLIED is False
