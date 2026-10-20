"""Locks: ``Csp`` presets honour later field edits; ``stamp_nonce(tags=)`` is honoured."""

from __future__ import annotations

import dataclasses
import unittest

from ux_dom.dom import div, script, style
from ux_dom.plugins import Csp
from ux_dom.plugins.csp import (
    CspPolicy,
    policy_dev,
    policy_prod,
    policy_report_only,
    stamp_nonce,
)


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

    def test_from_policy_round_trips_every_field(self):
        # Every CspPolicy field set off-default: a field dropped by
        # from_policy or to_policy breaks the round trip.
        values = {
            "strict_dynamic": False,
            "script_hosts": ("https://s.example",),
            "style_hosts": ("https://c.example",),
            "style_unsafe_inline": True,
            "script_unsafe_inline_legacy": True,
            "img_src": ("'self'",),
            "connect_src": ("wss://w.example",),
            "font_src": ("https://f.example",),
            "frame_ancestors": "'self'",
            "base_uri": "'none'",
            "object_src": "'self'",
            "form_action": "'none'",
            "upgrade_insecure": True,
            "report_uri": "/csp-report",
            "extra_directives": {"worker-src": "'none'"},
            "report_only": True,
            "debug_header": True,
            "nonce_bytes": 48,
        }
        self.assertEqual(set(values), {f.name for f in dataclasses.fields(CspPolicy)})
        pol = CspPolicy(**values)
        self.assertEqual(Csp.from_policy(pol).to_policy(), pol)

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
