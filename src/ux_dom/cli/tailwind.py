"""CSS *path* helpers for WebAssets trees — not the product compiler.

Product command: ``uxcompose build`` (``ux_compose.tailwind`` finds / downloads
/ invokes the Tailwind CLI). This module only knows where CSS files sit for
leftover ``uxdom build`` / Document verify:

- input:  ``assets/css/input.css``
- output: ``assets/static/file/css/output.css``  (WebAssets ``static.css``)

Product convention SSoT is ``ux_compose.tailwind.discover_css_io`` (consults
``WebAssets.static.css`` when ux-dom is installed). This copy is the leftover
path helper and does **not** download, cache, or call npx.

``argv_with_io`` is trivial CLI glue leftover verify may use when a binary is
already on PATH.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

__all__ = [
    "argv_with_io",
    "discover_css_io",
]


def argv_with_io(
    argv: Sequence[str],
    *,
    input_css: Path,
    output_css: Path,
    minify: bool = False,
    watch: bool = False,
) -> list[str]:
    out = list(argv)
    out.extend(["-i", str(input_css), "-o", str(output_css)])
    if minify:
        out.append("--minify")
    elif watch:
        out.append("--watch")
    return out


def discover_css_io(root: Path) -> Optional[tuple[Path, Path]]:
    """Resolve input/output CSS the same way WebAssets layout does.

    Leftover verify helper. Product convention SSoT is
    ``ux_compose.tailwind.discover_css_io``.
    """
    assets = Path(root) / "assets"
    input_css = assets / "css" / "input.css"
    if not input_css.is_file():
        alt = assets / "input.css"
        if alt.is_file():
            input_css = alt
        elif (Path(root) / "app" / "tailwindcss.py").is_file():
            input_css = assets / "css" / "input.css"
        else:
            return None
    output_css = assets / "static" / "file" / "css" / "output.css"
    output_css.parent.mkdir(parents=True, exist_ok=True)
    return input_css, output_css
