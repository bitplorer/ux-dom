# Copyright (c) 2026 ux-dom
"""Copy UI kit sources into an app (shadcn-style ownable components)."""

from __future__ import annotations

import re
import shutil
from importlib import import_module
from pathlib import Path

from ux_dom.ui.catalog import CATALOG


class UiCopyError(RuntimeError):
    pass


_IMPORT_REWRITES = [
    (re.compile(r"from ux_dom\.ui\.tokens import"), "from .tokens import"),
    (re.compile(r"from ux_dom\.ui\.button import"), "from .button import"),
    (re.compile(r"from ux_dom\.ui\.([a-zA-Z0-9_]+) import"), r"from .\1 import"),
    (re.compile(r"from ux_dom\.ui import"), "from . import"),
]

# stem → other catalog stems that must travel with a copy
_DEPS: dict[str, tuple[str, ...]] = {
    "dialog": ("button",),
    "channel_bridge": ("button",),
    "datepicker": ("input",),
    "slider": (),
    "carousel": (),
    "toast": (),
    "chart": (),
}


def copy_component(
    name: str,
    *,
    dest_dir: Path,
    force: bool = False,
) -> Path:
    """
    Copy a ``ux_dom.ui`` module into ``dest_dir`` for local ownership.

    ::

        copy_component("button", dest_dir=Path("app/components/ui"))
    """
    key = name.strip().lower().replace("-", "_")
    if key not in CATALOG:
        for k, meta in CATALOG.items():
            if meta["name"].lower() == key:
                key = k
                break
    if key not in CATALOG:
        raise UiCopyError(
            f"unknown UI component {name!r}; choose from {sorted(CATALOG)}"
        )
    meta = CATALOG[key]
    mod = import_module(meta["module"])
    src = Path(mod.__file__).resolve()  # type: ignore[arg-type]
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Always ensure tokens companion for style helpers
    tokens_mod = import_module("ux_dom.ui.tokens")
    tokens_src = Path(tokens_mod.__file__).resolve()  # type: ignore[arg-type]
    tokens_dst = dest_dir / "tokens.py"
    if not tokens_dst.exists() or force:
        shutil.copy2(tokens_src, tokens_dst)

    for dep in _DEPS.get(key, ()):
        copy_component(dep, dest_dir=dest_dir, force=force)

    dest = dest_dir / src.name
    if dest.exists() and not force:
        raise UiCopyError(f"{dest} exists (use --force)")
    text = src.read_text(encoding="utf-8")
    for pat, repl in _IMPORT_REWRITES:
        text = pat.sub(repl, text)
    dest.write_text(text, encoding="utf-8")
    init = dest_dir / "__init__.py"
    if not init.exists():
        init.write_text(
            '"""App-local UI kit (copied from ux_dom.ui — edit freely)."""\n',
            encoding="utf-8",
        )
    return dest
