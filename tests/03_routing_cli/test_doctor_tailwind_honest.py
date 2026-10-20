"""F-22: doctor reports only checks that can fail; CSS is a footer note, not a check."""

from __future__ import annotations

from ux_dom.cli.doctor import CSS_NOTE, format_report, run_doctor


def test_tailwind_is_not_a_check():
    report = run_doctor()
    assert "tailwind" not in {c.name for c in report.checks}
    assert "tailwind" not in {c["name"] for c in report.to_dict()["checks"]}


def test_css_note_is_a_footer_not_a_check_row():
    text = format_report(run_doctor())
    assert text.splitlines()[-1] == CSS_NOTE
    assert "uxcompose build" in CSS_NOTE
    rows = [ln for ln in text.splitlines() if ln.lstrip().startswith("[")]
    assert not any("uxcompose build" in ln for ln in rows)
