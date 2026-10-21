"""Live Chromium: a boolean attribute's rendered state is the Python value (#122).

Each spec boolean attribute is rendered with ``True``, ``False`` and ``None``
on an element that has it, and Chromium reports the element's IDL property
(``input.checked``, ``button.disabled``, ``option.selected`` ...). ``True``
must turn it on; ``False`` and ``None`` must leave it off. The #44
``RadioInput`` / ``CheckboxInput`` elements and a parsed
``checked="false"`` are checked the same way. Render contract:
``tests/07_resilience/test_boolean_attributes.py``.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from ux_dom.dom import button, defHTML, details, form, input_, option, select, summary
from ux_dom.elements import CheckboxInput, RadioInput

from browser_gate import NODE, require_browser

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "boolean_state_harness.mjs"

# attribute -> (build(value), selector, IDL property)
CASES = {
    "checked": (lambda v: input_(type="checkbox", checked=v), "input", "checked"),
    "disabled": (lambda v: button("b", disabled=v), "button", "disabled"),
    "selected": (
        lambda v: select(option("a"), option("b", selected=v)),
        "option:nth-of-type(2)",
        "selected",
    ),
    "required": (lambda v: input_(required=v), "input", "required"),
    "readonly": (lambda v: input_(readonly=v), "input", "readOnly"),
    "multiple": (lambda v: select(option("a"), multiple=v), "select", "multiple"),
    "open": (lambda v: details(summary("s"), open=v), "details", "open"),
    "novalidate": (lambda v: form(novalidate=v), "form", "noValidate"),
    "formnovalidate": (lambda v: button("b", formnovalidate=v), "button", "formNoValidate"),
    "autofocus": (lambda v: input_(autofocus=v), "input", "autofocus"),
    "RadioInput": (lambda v: RadioInput(name="r", checked=v), "input", "checked"),
    "CheckboxInput": (lambda v: CheckboxInput(name="c", checked=v), "input", "checked"),
}


def _chromium(cases):
    proc = subprocess.run(
        [NODE, str(HARNESS)],
        input=json.dumps(cases),
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise AssertionError(f"harness rc={proc.returncode}\n{proc.stderr}")
    return json.loads(proc.stdout)


class TestBooleanStateInChromium(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_browser()
        cls.keys = [(name, v) for name in CASES for v in (True, False, None)]
        cases = []
        for name, value in cls.keys:
            build, selector, prop = CASES[name]
            cases.append([build(value).__render__(pretty=False), selector, prop])
        cls.state = dict(zip(cls.keys, _chromium(cases)))

    def test_true_turns_the_state_on(self):
        for name in CASES:
            with self.subTest(name):
                self.assertIs(self.state[(name, True)], True)

    def test_false_and_none_leave_it_off(self):
        for name in CASES:
            for value in (False, None):
                with self.subTest(name, value=value):
                    self.assertIs(self.state[(name, value)], False)

    def test_parsed_checked_false_is_checked_like_the_browser(self):
        (tag,) = defHTML('<input type="checkbox" checked="false">')
        html = tag.__render__(pretty=False)
        self.assertEqual(_chromium([[html, "input", "checked"]]), [True])


if __name__ == "__main__":
    unittest.main()
