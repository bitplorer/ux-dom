# Copyright (c) 2026 ux-dom
"""Copy UI kit sources into an app (shadcn-style ownable components)."""

from __future__ import annotations

import ast
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


def _deps(src: Path) -> set[str]:
    """Catalog stems that ``src`` imports as ``from ux_dom.ui.<stem> import``."""
    tree = ast.parse(src.read_text(encoding="utf-8"))
    modules = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    return {m.split(".")[-1] for m in modules if m.startswith("ux_dom.ui.")} & set(CATALOG)


def _kit_imports(tree: ast.AST) -> dict[str, set[str]]:
    """``{stem: names}`` for every ``from ux_dom.ui.<stem> import names``."""
    out: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("ux_dom.ui."):
            stem = node.module.split(".")[-1]  # type: ignore[union-attr]
            out.setdefault(stem, set()).update(a.name for a in node.names)
    return out


def _keywords_used(tree: ast.AST, name: str) -> set[str]:
    return {
        kw.arg
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name
        for kw in node.keywords
        if kw.arg
    }


def _defined(tree: ast.Module) -> dict[str, ast.AST]:
    """Top-level names a module defines, mapped to their defining node."""
    out: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out[node.name] = node
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    out[t.id] = node
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                out[(a.asname or a.name).split(".")[0]] = node
    return out


def _accepts(fn: ast.AST, keywords: set[str]) -> set[str]:
    """Keywords from ``keywords`` that function ``fn`` does not accept."""
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or fn.args.kwarg:
        return set()
    params = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
    return keywords - params


def _stale_kit_files(src: Path, dest_dir: Path) -> list[str]:
    """What ``src`` needs from kit files already in ``dest_dir`` that they lack."""
    src_tree = ast.parse(src.read_text(encoding="utf-8"))
    missing: list[str] = []
    for stem, names in sorted(_kit_imports(src_tree).items()):
        dep = dest_dir / f"{stem}.py"
        if not dep.exists():
            continue
        defined = _defined(ast.parse(dep.read_text(encoding="utf-8")))
        for name in sorted(names):
            if name not in defined:
                missing.append(f"{dep.name}: {name}")
                continue
            for kw in sorted(_accepts(defined[name], _keywords_used(src_tree, name))):
                missing.append(f"{dep.name}: {name}({kw}=)")
    return missing


def copy_component(
    name: str,
    *,
    dest_dir: Path,
    force: bool = False,
) -> Path:
    """
    Copy a ``ux_dom.ui`` module into ``dest_dir`` for local ownership.

    Kit modules it imports travel with it. When ``force`` is off, a
    dependency file that already exists in ``dest_dir`` is kept as is;
    if that older copy lacks a name or keyword the new module uses,
    :class:`UiCopyError` names them and nothing more is written.

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
    return _copy(key, Path(dest_dir), force, set())


def _copy(key: str, dest_dir: Path, force: bool, seen: set[str]) -> Path:
    seen.add(key)  # cycle guard for the dependency walk
    meta = CATALOG[key]
    mod = import_module(meta["module"])
    src = Path(mod.__file__).resolve()  # type: ignore[arg-type]
    dest_dir.mkdir(parents=True, exist_ok=True)
    if not force:
        stale = _stale_kit_files(src, dest_dir)
        if stale:
            raise UiCopyError(
                f"{src.name} needs kit code your existing copies in {dest_dir} lack: "
                f"{', '.join(stale)}. Re-run with --force to refresh them "
                "(overwrites local edits), or update those files by hand."
            )

    # Always ensure tokens companion for style helpers
    tokens_mod = import_module("ux_dom.ui.tokens")
    tokens_src = Path(tokens_mod.__file__).resolve()  # type: ignore[arg-type]
    tokens_dst = dest_dir / "tokens.py"
    if not tokens_dst.exists() or force:
        shutil.copy2(tokens_src, tokens_dst)

    dest = dest_dir / src.name
    if dest.exists() and not force:
        raise UiCopyError(f"{dest} exists (use --force)")
    for dep in sorted(_deps(src) - seen):
        if force or not (dest_dir / f"{dep}.py").exists():
            _copy(dep, dest_dir, force, seen)
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
