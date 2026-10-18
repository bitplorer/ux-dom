"""F-22: doctor must not green-wash an unchecked Tailwind probe."""

from __future__ import annotations

from ux_dom.cli.doctor import run_doctor


def test_tailwind_check_is_not_a_fake_pass():
    report = run_doctor()
    tw = next(c for c in report.checks if c.name == "tailwind")
    assert tw.ok is False
    assert tw.level == "info"
    assert "not checked" in tw.detail.lower() or "uxcompose" in tw.detail.lower()
    assert report.ok is True  # info-level non-ok must not fail the report
