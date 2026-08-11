"""TailwindCommand integration and CLI flags."""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from ux_dom import WebAssets
from ux_dom.settings.commands import TailwindCommand


class TestTailwindAvailability(unittest.TestCase):
    def _cmd(self, tmp: Path) -> TailwindCommand:
        # Bypass heavy init side effects by constructing carefully
        wa = WebAssets(base_dir=tmp, sub_dir="assets", dry_run=True)
        with patch.object(TailwindCommand, "init_tailwind_project", lambda self: None):
            # TailwindCommand __post_init__ calls init; dry assets ok
            try:
                return TailwindCommand(
                    file_path=str(tmp / "tailwindcss.py"),
                    webassets=wa,
                    minify=True,
                )
            except Exception:
                # older path expectations — create minimal files
                (tmp / "tailwindcss.py").write_text("#\n")
                return TailwindCommand(
                    file_path=str(tmp / "tailwindcss.py"),
                    webassets=wa,
                    minify=True,
                )

    def test_available_returns_bool_true(self):
        with TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "tailwindcss.py").write_text("x=1\n")
            with patch.object(
                TailwindCommand, "init_tailwind_project", lambda self: None
            ):
                with patch.object(
                    TailwindCommand,
                    "is_tailwindcss_available",
                    lambda self: True,
                ):
                    # unit the method itself
                    pass
            fake = MagicMock()
            # call unbound-style by patching subprocess
            with patch("ux_dom.settings.commands.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess(
                    args=["which", "tailwindcss"], returncode=0
                )
                with patch.object(
                    TailwindCommand, "init_tailwind_project", lambda self: None
                ):
                    cmd = object.__new__(TailwindCommand)
                    cmd.tailwindcss = "tailwindcss"
                    cmd._root_dir = tmp
                    result = TailwindCommand.is_tailwindcss_available(cmd)
                self.assertIs(result, True)
                self.assertIsInstance(result, bool)

    def test_available_returns_bool_false(self):
        with TemporaryDirectory() as td:
            tmp = Path(td)
            with patch("ux_dom.settings.commands.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess(
                    args=["which", "tailwindcss"], returncode=1
                )
                cmd = object.__new__(TailwindCommand)
                cmd.tailwindcss = "tailwindcss"
                cmd._root_dir = tmp
                result = TailwindCommand.is_tailwindcss_available(cmd)
                self.assertIs(result, False)


class TestAsyncRunModes(unittest.TestCase):
    def test_watch_does_not_communicate(self):
        import asyncio

        async def run():
            cmd = object.__new__(TailwindCommand)
            cmd.tailwindcss = "tailwindcss"
            cmd.minify = False
            cmd._root_dir = Path("/tmp")
            cmd._input_file = Path("/tmp/in.css")
            cmd._output_file = Path("/tmp/out.css")

            proc = MagicMock()
            proc.returncode = None
            proc.pid = 1234
            proc.communicate = MagicMock(
                side_effect=AssertionError(
                    "communicate must not be called in watch mode"
                )
            )

            async def fake_exec(*a, **k):
                return proc

            with patch(
                "ux_dom.settings.commands.asyncio.create_subprocess_exec", fake_exec
            ):
                result = await TailwindCommand.async_run(cmd)
            self.assertIs(result, proc)
            proc.communicate.assert_not_called()

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()


class TestTailwindV4Compat(unittest.TestCase):
    def test_construct_writes_v4_input_without_init_subcommand(self):
        import tempfile
        from pathlib import Path

        from ux_dom import WebAssets
        from ux_dom.settings.commands import TailwindCommand

        d = Path(tempfile.mkdtemp())
        wa = WebAssets(base_dir=d, dry_run=False)
        cmd = TailwindCommand(file_path=d / "app.py", webassets=wa, minify=True)
        self.assertTrue(cmd._input_file.exists())
        text = cmd._input_file.read_text(encoding="utf-8")
        # v4 CSS-first entry (or v3 directives if CLI is v3)
        self.assertTrue(
            '@import "tailwindcss"' in text or "@tailwind base" in text,
            text[:200],
        )
        self.assertIn(cmd._tailwind_major(), (3, 4))
