"""Locks: ``Csp`` presets honour later field edits; ``stamp_nonce(tags=)`` is honoured."""

from __future__ import annotations

import dataclasses
import unittest

from ux_dom.dom import div, script, style
from ux_dom.plugins import Csp
from ux_dom.plugins.csp import policy_dev, policy_prod, policy_report_only, stamp_nonce


class TestCspFieldsAfterPreset(unittest.TestCase):
    def test_mutate_after_prod(self):
        c = Csp.prod()
        c.debug_header = True
        c.script_hosts = ["https://x.example"]
        pol = c.to_policy()
        self.assertIs(pol.debug_header, True)
        self.assertEqual(pol.script_hosts, ("https://x.example",))

    def test_replace_after_prod(self):
        c = dataclasses.replace(Csp.prod(), upgrade_insecure=False)
        self.assertIs(c.to_policy().upgrade_insecure, False)
        self.assertNotIn("upgrade-insecure-requests", c.to_policy().build("n"))

    def test_presets_header_unchanged(self):
        for preset, policy in (
            (Csp.dev(), policy_dev()),
            (Csp.prod(), policy_prod()),
            (Csp.report_only(), policy_report_only()),
        ):
            got = preset.to_policy()
            self.assertEqual(got.build("N"), policy.build("N"))
            self.assertEqual(got.report_only, policy.report_only)
            self.assertEqual(got.debug_header, policy.debug_header)
            self.assertEqual(got.nonce_bytes, policy.nonce_bytes)

    def test_explicit_policy_still_wins(self):
        pol = policy_prod(debug_header=True)
        self.assertIs(Csp(policy=pol).to_policy(), pol)


class TestStampNonceTags(unittest.TestCase):
    def test_script_only_skips_top_level_style(self):
        s = style("a{}")
        stamp_nonce([s], "NNNN", tags=("script",))
        self.assertNotIn("nonce", str(s))

    def test_script_only_skips_nested_style(self):
        tree = div(style("a{}"), div(script(src="/a.js")))
        stamp_nonce([tree], "NNNN", tags=("script",))
        html = str(tree)
        self.assertNotIn("<style nonce", html)
        self.assertEqual(html.count('nonce="NNNN"'), 1)

    def test_default_tags_unchanged(self):
        tree = div(style("a{}"), div(script(src="/a.js")))
        stamp_nonce([tree, style("b{}")], "NNNN")
        self.assertEqual(str(tree).count('nonce="NNNN"'), 2)


if __name__ == "__main__":
    unittest.main()
