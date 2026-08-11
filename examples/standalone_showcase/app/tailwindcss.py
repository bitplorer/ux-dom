"""CLI helper: python -m app.tailwindcss"""
from __future__ import annotations

import asyncio
from pathlib import Path

from ux_dom.settings.commands import TailwindCommand

from app import settings


def main() -> None:
    cmd = TailwindCommand(
        file_path=Path(__file__),
        webassets=settings.webassets,
        input_css=settings.INPUT_CSS,
        output_css=settings.OUTPUT_CSS,
        minify=not settings.DEBUG,
    )
    asyncio.run(cmd.async_run(wait=True))


if __name__ == "__main__":
    main()
