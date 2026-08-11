"""uxdom dashboard DX."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from ux_dom.cli.cli import app


class TestUxdomDashboard(unittest.TestCase):
    def test_cli_dashboard(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "dx"
            r = runner.invoke(
                app,
                [
                    "dashboard",
                    "--out",
                    str(out),
                    "--rounds",
                    "4",
                    "--warmup",
                    "1",
                    "--profile-rounds",
                    "2",
                ],
            )
            self.assertEqual(r.exit_code, 0, r.output)
            self.assertTrue((out / "dashboard.html").is_file())
            html = (out / "dashboard.html").read_text()
            self.assertIn("<svg", html)
            self.assertIn("ux-dom", html)


if __name__ == "__main__":
    unittest.main()
