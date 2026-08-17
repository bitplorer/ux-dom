"""Next-style ``.env`` loading for ``uxdom serve`` / ``dev`` / ``start``.

Load order (later files override earlier; process env always wins)::

    .env
    .env.local                 (skipped when UXDOM_ENV=test)
    .env.{development|production}
    .env.{development|production}.local

Does not expand interpolation. Values are stripped; empty keys ignored.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

__all__ = ["env_files_for", "load_env_files", "parse_env_text"]


def env_files_for(root: Path, *, mode: str = "dev") -> list[Path]:
    flavor = "production" if mode == "prod" else "development"
    names = [".env", ".env.local", f".env.{flavor}", f".env.{flavor}.local"]
    return [root / name for name in names]


def parse_env_text(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        out[key] = value
    return out


def load_env_files(
    root: Path,
    *,
    mode: str = "dev",
    environ: Optional[dict[str, str]] = None,
    skip_local: bool = False,
) -> list[Path]:
    """Merge dotenv files into ``environ`` without clobbering existing keys.

    Returns the files that were actually read.
    """
    import os

    target = environ if environ is not None else os.environ
    if skip_local or target.get("UXDOM_ENV") == "test":
        names = [".env", f".env.{'production' if mode == 'prod' else 'development'}"]
        files: Iterable[Path] = [root / n for n in names]
    else:
        files = env_files_for(root, mode=mode)

    read: list[Path] = []
    merged: dict[str, str] = {}
    for path in files:
        if not path.is_file():
            continue
        try:
            parsed = parse_env_text(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        merged.update(parsed)
        read.append(path)
    for key, value in merged.items():
        if key not in target:
            target[key] = value
    return read
