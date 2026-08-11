"""First-class DX: uxdom profile."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from ux_dom.cli.cli import app
from ux_dom.cli.profile import format_profile_report, run_profile


class TestProfileDx(unittest.TestCase):
    def test_run_profile_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "p95"
            report = run_profile(
                out=out, rounds=8, warmup=1, profile_rounds=4, open_hint=True
            )
            self.assertTrue((out / "report.html").is_file())
            self.assertTrue((out / "latency.json").is_file())
            self.assertTrue((out / "profile.speedscope.json").is_file())
            self.assertIn("latencies", report)
            text = format_profile_report(report)
            self.assertIn("uxdom profile", text)
            self.assertIn("p95", text)

    def test_cli_profile(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            result = runner.invoke(
                app,
                ["profile", "--out", str(out), "--rounds", "6", "--warmup", "1",
                 "--profile-rounds", "3"],
            )
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("uxdom profile", result.output)
            self.assertTrue((out / "profile.speedscope.json").is_file())


if __name__ == "__main__":
    unittest.main()
