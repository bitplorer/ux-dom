# Copyright (c) 2026 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
"""Style pipeline plugins (Tailwind CLI, none, …)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


class NullStyle:
    plugin_kind = "style"
    name = "null"

    def stylesheet_href(self) -> str:
        return ""

    async def build(self, *, watch: bool = False) -> Any:
        return None

    async def stop(self) -> None:
        return None


class TailwindStyle:
    """Wraps ``TailwindCommand`` as a StylePlugin for App composition.

    Requires a ``WebAssets`` instance (same as TailwindCommand).
    """

    plugin_kind = "style"
    name = "tailwind"

    def __init__(
        self,
        webassets: Any,
        *,
        file_path: Optional[Any] = None,
        input_css: str = "tailwind.css",
        output_css: str = "styles.css",
        minify: bool = False,
    ):
        self.webassets = webassets
        self.file_path = file_path or Path.cwd() / "__ux_dom_app__.py"
        self.input_css = input_css
        self.output_css = output_css
        self.minify = minify
        self._cmd = None

    def _owned_by_cli(self) -> bool:
        """Compose/CLI already runs the standalone Tailwind — skip a second watch."""
        import os

        return os.environ.get("UXDOM_TAILWIND_OWNED", "") in {"1", "true", "True"}

    def _command(self):
        if self._cmd is None:
            from ux_dom.settings.commands import TailwindCommand

            self._cmd = TailwindCommand(
                file_path=self.file_path,
                webassets=self.webassets,
                input_css=self.input_css,
                output_css=self.output_css,
                minify=self.minify,
            )
        return self._cmd

    def stylesheet_href(self) -> str:
        return f"/css/{self.output_css}"

    async def build(self, *, watch: bool = False) -> Any:
        if self._owned_by_cli():
            return None
        cmd = self._command()
        if watch and not self.minify:
            return await cmd.async_run(wait=False)
        return await cmd.async_run(wait=True)

    async def stop(self) -> None:
        if self._cmd is not None:
            await self._cmd.async_stop()


__all__ = ["NullStyle", "TailwindStyle"]
