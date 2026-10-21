#!/usr/bin/env python3
"""Persisted, machine-readable code map of a Python repo (stdlib only, AST-based).

Usage::

    python scripts/codemap.py                  # rewrite every shard, drop orphans
    python scripts/codemap.py --write-changed  # rewrite stale shards (PR authors)
    python scripts/codemap.py --check          # exit 1: stale shards / broken refs
    python scripts/codemap.py --module pkg.x   # print one module's entry
    python scripts/codemap.py --feature ID     # print one feature and its modules
    python scripts/codemap.py --claims DOC     # print one doc's claims with lines

This file is identical in every repo that vendors it; everything repo-specific
lives in ``[tool.codemap]`` of a ``pyproject.toml`` (the repo root's, else the
one directory down that has the table; ``--config`` overrides). Paths in the
config are relative to the repo root (``--root``, default: this script's
parent's parent). The map is sharded under ``out_dir``: ``index.json`` plus one
``modules/<dotted.name>.json`` per module and ``assets/<dotted.path>.json`` per
asset. Output is deterministic: sorted keys, sorted lists, no timestamps or
commit hashes, so a shard only changes when its module (or a reference to it)
does. ``index.json`` names this generator's version and sha256 so a repo's
vendored copy can be verified. See docs/internals/CODEMAP.md.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

VERSION = "2.0.0"
SCHEMA = 2
SCRIPT = Path(__file__).resolve()

IMPORT_KINDS = ("module_level", "function_level", "type_checking")
RUNTIME_KINDS = ("module_level", "function_level")  # edges layer rules apply to
SKIP_DIRS = {
    "__pycache__",
    "node_modules",
    ".git",
    ".venv",
    "venv",
    ".tox",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
# Constructors whose module-level result is reported as an ASGI app.
ASGI_FACTORIES = {"FastAPI", "Starlette", "Litestar", "Quart"}
CONFIG_KEYS = {
    "packages",
    "out_dir",
    "layers",
    "layer_rules",
    "layer_exceptions",
    "allowed_cycles",
    "assets",
    "public_api",
    "consumers",
    "self_files",
    "features",
    "domain",
    "narrative",
    "distributions",
    "claims_docs",
    "claims_exclude",
}
FEATURE_KEYS = {"id", "purpose", "modules", "symbols", "assets", "tests", "docs"}
FEATURE_ID = re.compile(r"[a-z][a-z0-9-]*")
DOMAIN_KEYS = {"domain", "public_api", "owns", "non_goals", "depends_on", "law"}
LAW_KEYS = {"url", "concepts"}
ENV_NAME = re.compile(r"[A-Z][A-Z0-9]*_[A-Z0-9_]*[A-Z0-9]")
FENCE = re.compile(r"^\s*(```|~~~)")
OWNS_KEYS = {"concept", "modules", "symbols"}
NON_GOAL_KEYS = {"concept", "owner", "keywords"}
DEPENDS_KEYS = {"distribution", "imports", "names"}
# A foreign module path is private when a segment starts with ``_`` (not a
# dunder) or is one of these implementation-detail segment names.
PRIVATE_SEGMENTS = {"src", "internal", "internals", "impl", "_impl"}


# --------------------------------------------------------------------- config


@dataclass
class Package:
    name: str  # import name, e.g. ``ux_dom``
    path: Path  # package directory
    import_root: Path  # directory on sys.path (the package's parent)


@dataclass
class Config:
    root: Path
    source: Path  # file the config was read from
    packages: list[Package]
    out_dir: Path
    layers: dict[str, str] = field(default_factory=dict)
    layer_rules: dict[str, list[str]] = field(default_factory=dict)
    layer_exceptions: list[tuple[str, str]] = field(default_factory=list)
    allowed_cycles: list[list[str]] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    public_rule: str = "all_or_derived"
    public_packages: list[str] = field(default_factory=list)
    consumers: dict[str, tuple[str, ...]] = field(default_factory=dict)
    self_files: set[str] = field(default_factory=set)
    features: Path | None = None
    domain: Path | None = None
    narrative: list[str] = field(default_factory=list)
    projects: list[Path] = field(default_factory=list)
    distributions: dict[str, str] = field(default_factory=dict)
    claims_docs: list[str] = field(default_factory=list)
    claims_exclude: list[str] = field(default_factory=list)

    @property
    def names(self) -> set[str]:
        return {p.name for p in self.packages}

    def rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix()

    def is_internal(self, dotted: str) -> bool:
        return _in_packages(dotted, self.names)

    def roots_pattern(self) -> str:
        """Regex alternation of the package names, for citation scanners."""
        return "|".join(sorted(map(re.escape, self.names)))


def _in_packages(dotted: str, packages: set[str]) -> bool:
    return dotted.partition(".")[0] in packages


def _find_config(root: Path) -> Path:
    candidates = [root / "pyproject.toml"]
    candidates += sorted(
        p / "pyproject.toml"
        for p in root.iterdir()
        if p.is_dir() and p.name not in SKIP_DIRS
    )
    found = [c for c in candidates if c.is_file() and "codemap" in _tool_tables(c)]
    if not found:
        raise SystemExit(
            f"codemap: no [tool.codemap] in {root}/pyproject.toml or one level down"
        )
    if found[0] != candidates[0] and len(found) > 1:
        names = ", ".join(str(f.relative_to(root)) for f in found)
        raise SystemExit(
            f"codemap: several [tool.codemap] tables ({names}); use --config"
        )
    return found[0]


def _tool_tables(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh).get("tool", {})


def load_config(root: Path, config_path: Path | None = None) -> Config:
    root = root.resolve()
    source = (config_path or _find_config(root)).resolve()
    raw = _tool_tables(source).get("codemap")
    if not isinstance(raw, dict):
        raise SystemExit(f"codemap: {source} has no [tool.codemap] table")
    unknown = sorted(set(raw) - CONFIG_KEYS)
    if unknown:
        raise SystemExit(f"codemap: unknown [tool.codemap] keys: {', '.join(unknown)}")

    packages = []
    for rel in raw.get("packages", []):
        path = (root / rel).resolve()
        if not path.is_dir():
            raise SystemExit(f"codemap: package directory {rel!r} does not exist")
        packages.append(Package(path.name, path, path.parent))
    if not packages:
        raise SystemExit("codemap: [tool.codemap] packages is empty")
    if len({p.name for p in packages}) != len(packages):
        raise SystemExit("codemap: two packages share an import name")

    def edge(text: str) -> tuple[str, str]:
        a, sep, b = text.partition("->")
        if not sep:
            raise SystemExit(f"codemap: layer_exceptions entry {text!r} needs 'a -> b'")
        return a.strip(), b.strip()

    public = raw.get("public_api", {})
    rule = public.get("rule", "all_or_derived")
    if rule not in ("all_or_derived", "all_only"):
        raise SystemExit(
            f"codemap: public_api.rule {rule!r} is not all_or_derived|all_only"
        )
    # Entry points come from the config's pyproject plus the nearest pyproject
    # above each package, so every sub-project of a multi-project repo counts.
    projects = {source} if source.name == "pyproject.toml" else set()
    for pkg in packages:
        for d in pkg.path.parents:
            if (d / "pyproject.toml").is_file():
                projects.add(d / "pyproject.toml")
                break
            if d == root:
                break
    features = raw.get("features")
    domain = raw.get("domain")
    return Config(
        root=root,
        source=source,
        packages=packages,
        out_dir=root / raw.get("out_dir", "docs/internals/codemap"),
        layers=dict(raw.get("layers", {})),
        layer_rules={k: list(v) for k, v in raw.get("layer_rules", {}).items()},
        layer_exceptions=[edge(e) for e in raw.get("layer_exceptions", [])],
        allowed_cycles=[sorted(c) for c in raw.get("allowed_cycles", [])],
        assets=list(raw.get("assets", [])),
        public_rule=rule,
        public_packages=list(public.get("packages", [p.name for p in packages])),
        consumers={k.strip("/"): tuple(v) for k, v in raw.get("consumers", {}).items()},
        self_files=set(raw.get("self_files", [])),
        features=root / features if features else None,
        domain=root / domain if domain else None,
        narrative=list(raw.get("narrative", [])),
        projects=sorted(projects),
        distributions=dict(raw.get("distributions", {})),
        claims_docs=list(raw.get("claims_docs", [])),
        claims_exclude=list(raw.get("claims_exclude", [])),
    )


def generator_identity() -> dict:
    return {
        "name": "codemap",
        "version": VERSION,
        "sha256": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    }


def layer_of(cfg: Config, name: str) -> str:
    """Layer for a dotted module name (or ``pkg/...`` asset directory).

    Longest matching prefix wins; a prefix that is a package name matches only
    that package's ``__init__``, so every subpackage must be placed. With no
    ``layers`` configured every module's layer is ``""``.
    """
    if not cfg.layers:
        return ""
    dotted = name.replace("/", ".")
    best = ""
    for prefix in cfg.layers:
        hit = dotted == prefix or (
            prefix not in cfg.names and dotted.startswith(prefix + ".")
        )
        if hit and len(prefix) > len(best):
            best = prefix
    return cfg.layers.get(best, "unknown")


def _walk(base: Path, exts: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if fn.endswith(exts):
                out.append(Path(dirpath) / fn)
    return out


def tracked_files(cfg: Config, tops: list[str]) -> list[Path] | None:
    """Git-tracked files under *tops*; None when *cfg.root* is in no checkout
    (or git is not installed). Any other git failure exits with git's message:
    silently walking instead would count untracked files."""

    def git(*args: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(["git", *args], cwd=cfg.root, capture_output=True)

    def failed(proc: subprocess.CompletedProcess[bytes], what: str) -> SystemExit:
        err = proc.stderr.decode("utf-8", "replace").strip()
        return SystemExit(f"codemap: git {what} failed: {err}")

    try:
        probe = git("rev-parse", "--is-inside-work-tree")
    except FileNotFoundError:
        return None
    if probe.returncode:
        # A corrupt repository also says "not a git repository"; only a root
        # with no .git at or above it is genuinely outside a checkout.
        in_checkout = any((d / ".git").exists() for d in [cfg.root, *cfg.root.parents])
        if b"not a git repository" in probe.stderr and not in_checkout:
            return None
        raise failed(probe, "rev-parse")
    listed = git("ls-files", "-z", "--", *tops)
    if listed.returncode:
        raise failed(listed, "ls-files")
    return [cfg.root / rel for rel in listed.stdout.decode("utf-8").split("\0") if rel]


def consumer_files(cfg: Config) -> list[Path]:
    """Git-tracked files under the ``consumers`` dirs (so untracked scratch
    files never change the map); falls back to walking outside a git checkout."""
    tops = sorted(cfg.consumers)
    paths = tracked_files(cfg, tops)
    if paths is None:
        paths = [p for top in tops for p in _walk(cfg.root / top, ("",))]
    out = []
    for p in paths:
        rel = cfg.rel(p)
        top = next((t for t in tops if rel.startswith(t + "/")), None)
        if (
            top is not None
            and p.name.endswith(cfg.consumers[top])
            and rel not in cfg.self_files
            and not SKIP_DIRS.intersection(p.parts)
            and p.is_file()
        ):
            out.append(p)
    return sorted(set(out))


def discover(cfg: Config) -> tuple[dict[str, Path], dict[str, Path]]:
    """Return ``({dotted module: path}, {asset key: path})``.

    An asset inside a package is keyed by its path from the import root
    (``pkg/scripts/x.js``); any other asset by its repo-relative path.
    """
    mods: dict[str, Path] = {}
    for pkg in cfg.packages:
        for p in _walk(pkg.path, (".py",)):
            dotted = p.relative_to(pkg.import_root).as_posix()[:-3].replace("/", ".")
            if dotted.endswith(".__init__"):
                dotted = dotted[: -len(".__init__")]
            mods[dotted] = p
    assets: dict[str, Path] = {}
    for pattern in cfg.assets:
        for p in sorted(cfg.root.glob(pattern)):
            if not p.is_file() or SKIP_DIRS.intersection(p.parts):
                continue
            owner = next((k for k in cfg.packages if p.is_relative_to(k.path)), None)
            key = p.relative_to(owner.import_root).as_posix() if owner else cfg.rel(p)
            assets[key] = p
    return mods, assets


# ------------------------------------------------------------------------ AST


def _ids(node: ast.AST) -> set[int]:
    return {id(n) for n in ast.walk(node)}


def _is_main_guard(node: ast.AST) -> bool:
    return isinstance(node, ast.If) and "__name__" in ast.unparse(node.test)


def _type_checking_body(node: ast.AST) -> list[ast.stmt]:
    """Body of ``if TYPE_CHECKING:`` / ``if typing.TYPE_CHECKING:``, else ``[]``.
    Only that body is type-only; ``else:`` and ``if not TYPE_CHECKING:`` run."""
    if not isinstance(node, ast.If):
        return []
    test = node.test
    if (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    ):
        return node.body
    return []


def _top_level_stmts(body: list[ast.stmt]) -> list[ast.stmt]:
    """Statements executed at import time (descends into if/try/with, not defs)."""
    out: list[ast.stmt] = []
    for st in body:
        if _is_main_guard(st):
            continue
        out.append(st)
        if isinstance(st, ast.If):
            out += _top_level_stmts(st.body) + _top_level_stmts(st.orelse)
        elif isinstance(st, ast.Try):
            out += _top_level_stmts(st.body)
            for h in st.handlers:
                out += _top_level_stmts(h.body)
            out += _top_level_stmts(st.orelse) + _top_level_stmts(st.finalbody)
        elif isinstance(st, (ast.With, ast.AsyncWith)):
            out += _top_level_stmts(st.body)
    return out


def _doc_line(
    node: ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:
    for line in (ast.get_docstring(node) or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def _call_name(call: ast.Call, positional: bool = True) -> str:
    """``name=`` keyword (or first positional) string of a call, else ''."""
    for kw in call.keywords:
        if kw.arg == "name" and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    if positional and call.args and isinstance(call.args[0], ast.Constant):
        value = call.args[0].value
        return value if isinstance(value, str) else ""
    return ""


def _signature(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    tparams = getattr(fn, "type_params", None)
    tp = f"[{', '.join(ast.unparse(t) for t in tparams)}]" if tparams else ""
    ret = f" -> {ast.unparse(fn.returns)}" if fn.returns else ""
    return f"{tp}({ast.unparse(fn.args)}){ret}"


def _symbol(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> dict:
    entry: dict = {"doc": _doc_line(node)}
    if node.decorator_list:
        entry["decorators"] = [ast.unparse(d) for d in node.decorator_list]
    if isinstance(node, ast.ClassDef):
        entry["kind"] = "class"
        entry["bases"] = [ast.unparse(b) for b in [*node.bases, *node.keywords]]
        methods = {}
        for st in node.body:
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods[st.name] = _symbol(st)
        entry["methods"] = methods
    else:
        entry["kind"] = (
            "async function" if isinstance(node, ast.AsyncFunctionDef) else "function"
        )
        entry["signature"] = _signature(node)
    return entry


class ModuleInfo:
    def __init__(
        self,
        name: str,
        path: Path,
        mods: dict[str, Path],
        packages: set[str],
        root: Path | None = None,
    ):
        self.name = name
        self.path = path
        self.root = root
        self.is_pkg = path.name == "__init__.py"
        self.text = path.read_text(encoding="utf-8")
        try:
            self.tree = ast.parse(self.text)
        except SyntaxError as exc:
            where = f"{self._where()}:{exc.lineno}"
            raise SystemExit(f"codemap: {where}: {exc.msg}") from None
        self.mods = mods
        self.packages = packages
        self.imports: dict[str, set[str]] = {k: set() for k in IMPORT_KINDS}
        self.external: dict[str, set[str]] = {k: set() for k in IMPORT_KINDS}
        self.defined: set[str] = set()  # def / class / assignment targets
        self.aliases: dict[str, str] = {}  # X = Y (Y a bare name)
        self.from_imports: dict[str, tuple[str, str]] = {}  # local -> (module, orig)
        self.reexports: set[str] = set()  # ``import x as x`` / ``from m import x as x``
        self.stars: list[str] = []  # internal modules star-imported at module level
        self.all: list[str] | None = None
        self.all_errors: list[str] = []  # unreadable ``__all__`` (file:line: why)
        self.symbols: dict[str, dict] = {}
        self.asgi: list[str] = []
        self.strings: set[str] = set()  # short string constants (env var names, ...)
        self.commands: set[str] = set()  # CLI subcommand names declared here
        # External usage: ``module:Name`` (or a bare ``module``) per name used.
        self.ext_used: set[str] = set()
        # Top-level import name -> number of import statements.
        self.ext_sites: dict[str, int] = {}
        # (foreign ref, "isinstance pkg.m" / "subclass pkg.m.Cls") pairs.
        self.ext_hard: set[tuple[str, str]] = set()
        self._ext_refs: dict[str, str] = {}  # local name -> "module:Name"
        self._ext_mods: dict[str, set[str]] = {}  # local name -> imported modules
        self.ext_annotated: set[str] = set()  # names seen in type annotations
        self._scan()
        self._scan_external_usage()
        self._scan_cli_and_strings()

    def _where(self) -> str:
        if self.root and self.path.is_relative_to(self.root):
            return self.path.relative_to(self.root).as_posix()
        return str(self.path)

    def _internal(self, dotted: str) -> bool:
        return _in_packages(dotted, self.packages)

    # -- import resolution
    def _base(self, node: ast.ImportFrom) -> str:
        if not node.level:
            return node.module or ""
        parts = self.name.split(".")
        if not self.is_pkg:
            parts = parts[:-1]
        parts = parts[: len(parts) - (node.level - 1)]
        base = ".".join(parts)
        return base + ("." + node.module if node.module else "")

    def _longest_module(self, dotted: str) -> str | None:
        while dotted:
            if dotted in self.mods:
                return dotted
            dotted = dotted.rpartition(".")[0]
        return None

    def _targets(self, node: ast.Import | ast.ImportFrom) -> tuple[set[str], set[str]]:
        """``(internal modules, external modules)`` named by an import."""
        internal: set[str] = set()
        external: set[str] = set()
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        else:
            base = self._base(node)
            if not self._internal(base):
                return internal, ({base} if base else set())
            names = [
                f"{base}.{a.name}" if f"{base}.{a.name}" in self.mods else base
                for a in node.names
            ]
        for n in names:
            if self._internal(n):
                t = self._longest_module(n)
                if t and t != self.name:
                    internal.add(t)
            else:
                external.add(n)
        return internal, external

    def _scan(self) -> None:
        tc_ids: set[int] = set()
        fn_ids: set[int] = set()
        for n in ast.walk(self.tree):
            for st in _type_checking_body(n):
                tc_ids |= _ids(st)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                fn_ids |= _ids(n) - {id(n)}
        for st in self.tree.body:
            if _is_main_guard(st):
                fn_ids |= _ids(st)  # deferred: never runs on import
        for n in ast.walk(self.tree):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                kind = (
                    "type_checking"
                    if id(n) in tc_ids
                    else "function_level" if id(n) in fn_ids else "module_level"
                )
                internal, external = self._targets(n)
                self.imports[kind] |= internal
                self.external[kind] |= external
                self._bind_external(n)

        for st in _top_level_stmts(self.tree.body):
            if id(st) in tc_ids:
                continue
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.defined.add(st.name)
                self.symbols[st.name] = _symbol(st)
            elif isinstance(st, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = st.targets if isinstance(st, ast.Assign) else [st.target]
                for t in targets:
                    for n in ast.walk(t):
                        if isinstance(n, ast.Name):
                            self.defined.add(n.id)
                if (
                    isinstance(st, ast.Assign)
                    and len(st.targets) == 1
                    and isinstance(st.targets[0], ast.Name)
                ):
                    target = st.targets[0].id
                    if isinstance(st.value, ast.Name):
                        self.aliases[target] = st.value.id
                    elif isinstance(st.value, ast.Call):
                        func = st.value.func
                        called = (
                            func.attr
                            if isinstance(func, ast.Attribute)
                            else (func.id if isinstance(func, ast.Name) else "")
                        )
                        if called in ASGI_FACTORIES:
                            self.asgi.append(f"{self.name}:{target}")
                if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
                    self._read_all(st)
            elif (
                isinstance(st, ast.Expr)
                and isinstance(st.value, ast.Call)
                and isinstance(st.value.func, ast.Attribute)
                and isinstance(st.value.func.value, ast.Name)
                and st.value.func.value.id == "__all__"
            ):
                self._bad_all(st, f"``__all__.{st.value.func.attr}(...)``")
            elif isinstance(st, ast.Import):
                for a in st.names:
                    if a.asname and a.asname == a.name.rpartition(".")[2]:
                        self.reexports.add(a.asname)
            elif isinstance(st, ast.ImportFrom):
                base = self._base(st)
                for a in st.names:
                    if a.name == "*":
                        star = self._longest_module(base)
                        if star and star != self.name and self._internal(base):
                            self.stars.append(star)
                        continue
                    local = a.asname or a.name
                    self.from_imports[local] = (base, a.name)
                    if a.asname == a.name:
                        self.reexports.add(local)

    def _scan_cli_and_strings(self) -> None:
        for n in ast.walk(self.tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                if len(n.value) <= 80:
                    self.strings.add(n.value)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for d in n.decorator_list:
                    if (
                        isinstance(d, ast.Call)
                        and isinstance(d.func, ast.Attribute)
                        and d.func.attr == "command"
                    ):
                        name = _call_name(d)
                        self.commands.add(name or n.name.replace("_", "-"))
            if (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr in ("add_parser", "add_typer", "add_command")
            ):
                name = _call_name(n, positional=n.func.attr == "add_parser")
                if name:
                    self.commands.add(name)

    def _bind_external(self, n: ast.Import | ast.ImportFrom) -> None:
        """Record the local names a foreign import binds, and count the site."""
        if isinstance(n, ast.Import):
            for a in n.names:
                if not self._internal(a.name):
                    top = a.name.partition(".")[0]
                    self.ext_sites[top] = self.ext_sites.get(top, 0) + 1
                    self._ext_mods.setdefault(a.asname or top, set()).add(a.name)
            return
        base = self._base(n)
        if not base or self._internal(base):
            return
        top = base.partition(".")[0]
        self.ext_sites[top] = self.ext_sites.get(top, 0) + 1
        for a in n.names:
            ref = f"{base}:{a.name}"
            self.ext_used.add(ref)
            if a.name != "*":
                self._ext_refs[a.asname or a.name] = ref

    def _scan_external_usage(self) -> None:
        """Collect which foreign names this module uses, and how (see CODEMAP.md)."""
        refs, mods = self._ext_refs, self._ext_mods

        def resolve(node: ast.AST) -> str | None:
            if isinstance(node, ast.Name):
                return refs.get(node.id)
            chain: list[str] = []
            while isinstance(node, ast.Attribute):
                chain.append(node.attr)
                node = node.value
            if not isinstance(node, ast.Name) or node.id not in mods:
                return None
            full = ".".join([node.id, *reversed(chain)])
            imported = sorted(mods[node.id], key=len, reverse=True)
            for m in imported:
                if full.startswith(m + "."):
                    return f"{m}:{full[len(m) + 1 :].split('.')[0]}"
            return None

        annotation_ids: set[int] = set()
        for n in ast.walk(self.tree):
            notes: list[ast.AST | None] = []
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = n.args
                every = [
                    *args.posonlyargs,
                    *args.args,
                    *args.kwonlyargs,
                    args.vararg,
                    args.kwarg,
                ]
                notes += [a.annotation for a in every if a is not None]
                notes.append(n.returns)
            elif isinstance(n, ast.AnnAssign):
                notes.append(n.annotation)
            for note in notes:
                if note is not None:
                    annotation_ids |= _ids(note)
        accessed: set[str] = set()
        for n in ast.walk(self.tree):
            if isinstance(n, (ast.Name, ast.Attribute)):
                ref = resolve(n)
                if ref:
                    if isinstance(n, ast.Attribute):
                        accessed.add(ref.partition(":")[0])
                        self.ext_used.add(ref)
                    if id(n) in annotation_ids:
                        self.ext_annotated.add(ref)
            if isinstance(n, ast.ClassDef):
                for b in n.bases:
                    ref = resolve(b)
                    if ref:
                        self.ext_hard.add((ref, f"subclass {self.name}.{n.name}"))
            if (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id in ("isinstance", "issubclass")
                and len(n.args) == 2
            ):
                types = (
                    n.args[1].elts if isinstance(n.args[1], ast.Tuple) else [n.args[1]]
                )
                for t in types:
                    ref = resolve(t)
                    if ref:
                        self.ext_hard.add((ref, f"{n.func.id} {self.name}"))
        for dotted in mods.values():
            for m in dotted:
                if m not in accessed:
                    self.ext_used.add(m)

    def _bad_all(self, st: ast.stmt, why: str) -> None:
        self.all_errors.append(
            f"{self._where()}:{st.lineno}: {why}; ``__all__`` must be a literal "
            "list/tuple of strings, so the public API is recorded as unknown"
        )

    def _read_all(self, st: ast.stmt) -> None:
        """Read a literal ``__all__``; record anything else in ``all_errors``.

        A computed ``__all__`` cannot be read statically. The module's public
        set then falls back to the derived one and ``--check`` fails naming
        file:line, so a guessed surface is never recorded silently.
        """
        value = getattr(st, "value", None)
        if not (
            isinstance(value, (ast.List, ast.Tuple))
            and all(
                isinstance(e, ast.Constant) and isinstance(e.value, str)
                for e in value.elts
            )
        ):
            self._bad_all(st, "non-literal ``__all__``")
            return
        names = [e.value for e in value.elts]  # type: ignore[attr-defined]
        if isinstance(st, ast.AugAssign):
            if self.all is None:
                self._bad_all(st, "``__all__ +=`` before ``__all__ =``")
                return
            names = self.all + names
        self.all = names


# ---------------------------------------------------------------------- build


class CodeMap:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.mods, self.assets = discover(cfg)
        names = cfg.names
        self.info = {
            m: ModuleInfo(m, p, self.mods, names, cfg.root)
            for m, p in self.mods.items()
        }
        self._public: dict[str, list[str]] = {}
        self.problems: list[str] = [
            f"__all__: {e}" for i in self.info.values() for e in i.all_errors
        ]
        self.notices: list[str] = []  # unconfigured / empty sections (not failures)
        roots = cfg.roots_pattern()
        self._citation_re = re.compile(rf"(?:{roots})(?:\.\w+)*(?::\w+(?:\.\w+)*)?")
        self._import_dist: dict[str, str] = {}  # from depends_on ``imports``
        self.claim_lines: dict[str, list[dict]] = {}  # doc -> claims with lines

    def public(self, mod: str, _seen: frozenset[str] = frozenset()) -> list[str]:
        """``__all__`` if defined; else (rule ``all_or_derived``) non-underscore
        defs/classes/assignments plus PEP 484 re-exports (``x as x``) and
        star-import expansions; else (rule ``all_only``) nothing."""
        if mod in self._public:
            return self._public[mod]
        info = self.info[mod]
        if info.all is not None and not info.all_errors:
            names = set(info.all)
        elif self.cfg.public_rule == "all_only":
            names = set()
        else:
            names = {n for n in info.defined | info.reexports if not n.startswith("_")}
            for star in info.stars:
                if star not in _seen:
                    names |= set(self.public(star, _seen | {mod}))
        self._public[mod] = sorted(names)
        return self._public[mod]

    def public_unknown(self, mod: str, _seen: frozenset[str] = frozenset()) -> bool:
        """True when *mod*'s public set cannot be read: its ``__all__`` is not
        a literal, or it is derived from a star import of such a module."""
        info = self.info[mod]
        if info.all_errors:
            return True
        if info.all is not None or self.cfg.public_rule == "all_only":
            return False
        return any(
            self.public_unknown(star, _seen | {mod})
            for star in info.stars
            if star not in _seen
        )

    def defining_module(
        self, mod: str, name: str, _seen: frozenset[tuple[str, str]] = frozenset()
    ) -> str:
        """Follow re-exports / star imports / ``X = Y`` aliases to *name*'s home."""
        key = (mod, name)
        if key in _seen:
            return mod
        seen = _seen | {key}
        info = self.info[mod]
        if name in info.aliases and info.aliases[name] != name:
            target = info.aliases[name]
            if target in info.from_imports or target in info.defined:
                return self.defining_module(mod, target, seen)
        if name in info.defined:
            return mod
        if name in info.from_imports:
            base, orig = info.from_imports[name]
            if f"{base}.{orig}" in self.mods:
                return f"{base}.{orig}"
            if base in self.mods:
                return self.defining_module(base, orig, seen)
            return base  # external (or unresolved) source
        for star in info.stars:
            if name in self.public(star):
                return self.defining_module(star, name, seen)
        return mod

    def symbol_home(self, mod: str, name: str) -> str | None:
        """Internal module that *name* (looked up on *mod*) is, or is defined in."""
        if f"{mod}.{name}" in self.mods:
            return f"{mod}.{name}"
        if mod not in self.info:
            return None
        home = self.defining_module(mod, name)  # falls back to *mod* itself
        return home if home in self.mods else None

    def resolves(self, mod: str, name: str) -> bool:
        """Does ``mod:name`` (``name`` may be ``Class.method``) exist?"""
        head, _, rest = name.partition(".")
        if mod not in self.info:
            return False
        if not rest and f"{mod}.{head}" in self.mods:
            return True
        info = self.info[mod]
        known = (
            head in info.defined
            or head in info.from_imports
            or head in info.reexports
            or head in self.public(mod)
        )
        if not known:
            return False
        if not rest:
            return True
        home = self.defining_module(mod, head)
        if home not in self.info:
            return False
        target = self.info[home].aliases.get(head, head)
        sym = self.info[home].symbols.get(target)
        return bool(sym and sym.get("kind") == "class" and rest in sym["methods"])

    def dist_of(self, dotted: str) -> str:
        top = dotted.partition(":")[0].partition(".")[0]
        if top in sys.stdlib_module_names or top == "__future__":
            return "stdlib"
        return self._import_dist.get(top) or self.cfg.distributions.get(top, top)

    # -- consumers
    def _consumer_index(self) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
        """Heuristic (cheap regex, documented in CODEMAP.md):

        * every dotted token ``pkg.a.b.c`` resolves to its longest known module
          prefix (so ``patch("pkg.cli.doctor.run")`` counts for ``pkg.cli.doctor``);
        * ``from pkg.a import b`` counts ``pkg.a.b`` when that is a module;
        * a symbol named through a re-exporting module (``from pkg import X``,
          ``pkg.dom.div``) also counts for the module that defines it;
        * a path ``pkg/a/b.py`` counts for ``pkg.a.b``;
        * a bare package root counts only via ``import pkg`` / ``from pkg import``;
        * an asset counts when its file name (``x_element.js``) appears.
        """
        roots = self.cfg.roots_pattern()
        dotted_re = re.compile(rf"(?<![\w.])(?:{roots})(?:\.[A-Za-z_]\w*)+")
        from_re = re.compile(
            rf"from[ \t]+((?:{roots})(?:\.\w+)*)[ \t]+import[ \t]*"
            r"(?:\(([^)]*)\)|([^\n#;]*))"
        )
        root_re = {
            pkg: re.compile(
                rf"^\s*(?:import\s+{re.escape(pkg)}\b|from\s+{re.escape(pkg)}\s+import\b)",
                re.M,
            )
            for pkg in self.cfg.names
        }
        path_re = re.compile(rf"(?<![\w.])((?:{roots})/(?:\w+/)*\w+)\.py\b")
        mod_hits: dict[str, set[str]] = {m: set() for m in self.mods}
        asset_hits: dict[str, set[str]] = {a: set() for a in self.assets}
        basenames = {a: a.rpartition("/")[2] for a in self.assets}

        def longest(dotted: str) -> str | None:
            while dotted and dotted not in self.cfg.names:
                if dotted in self.mods:
                    return dotted
                dotted = dotted.rpartition(".")[0]
            return None

        def resolve(dotted: str) -> set[str]:
            """Module named by *dotted*, plus the defining module of a symbol
            accessed on it (``pkg.dom.div`` -> the module defining ``div``)."""
            pkg = dotted.partition(".")[0]
            mod = longest(dotted) or pkg
            out = {mod} if mod != pkg else set()
            rest = dotted[len(mod) + 1 :].split(".")[0] if dotted != mod else ""
            home = self.symbol_home(mod, rest) if rest else None
            if home and home not in self.cfg.names:
                out.add(home)
            return out

        files = consumer_files(self.cfg)
        if not self.cfg.consumers:
            self.notices.append(
                "consumers: not configured; every module's consumers is empty"
            )
        elif not files:
            self.notices.append("consumers: no tracked file matched")
        for p in files:
            text = p.read_text(encoding="utf-8", errors="replace")
            rel = self.cfg.rel(p)
            found: set[str] = set()
            for m in dotted_re.finditer(text):
                found |= resolve(m.group(0))
            for m in from_re.finditer(text):
                names = re.sub(r"#[^\n]*", "", m.group(2) or m.group(3) or "")
                for item in names.split(","):
                    words = item.split()
                    if words:
                        found |= resolve(f"{m.group(1)}.{words[0]}")
            for m in path_re.finditer(text):
                t = longest(m.group(1).replace("/", "."))
                if t:
                    found.add(t)
            for pkg, rx in root_re.items():
                if pkg in self.mods and rx.search(text):
                    found.add(pkg)
            for t in found:
                if t in mod_hits:
                    mod_hits[t].add(rel)
            for a, bn in basenames.items():
                if bn in text:
                    asset_hits[a].add(rel)
        return mod_hits, asset_hits

    # -- repo-level sections
    def entry_points(self) -> dict:
        scripts: dict[str, str] = {}
        groups: dict[str, dict[str, str]] = {}
        for pyproject in self.cfg.projects:
            if not pyproject.is_file():
                self.problems.append(
                    f"config: projects entry {self.cfg.rel(pyproject)} does not exist"
                )
                continue
            with pyproject.open("rb") as fh:
                data = tomllib.load(fh)
            project = data.get("project", {})
            scripts.update(project.get("scripts", {}))
            scripts.update(project.get("gui-scripts", {}))
            for group, table in project.get("entry-points", {}).items():
                groups.setdefault(group, {}).update(table)
            for name, ref in (
                data.get("tool", {}).get("poetry", {}).get("scripts", {}).items()
            ):
                if isinstance(ref, dict):
                    ref = ref.get("reference") or ref.get("callable") or ""
                scripts[name] = ref
        for where, table in [
            ("scripts", scripts),
            *((f"entry-points.{g}", t) for g, t in groups.items()),
        ]:
            for name, ref in table.items():
                self._check_ref(
                    f"entry point {where}.{name}", ref.split("[")[0].strip()
                )
        return {
            "scripts": dict(sorted(scripts.items())),
            "entry_points": {
                g: dict(sorted(t.items())) for g, t in sorted(groups.items())
            },
            "main_modules": sorted(m for m in self.mods if m.endswith(".__main__")),
            "asgi": sorted(a for i in self.info.values() for a in i.asgi),
        }

    def _check_ref(self, what: str, ref: str) -> None:
        mod, _, attr = ref.partition(":")
        if not self.cfg.is_internal(mod):
            return
        if mod not in self.mods:
            self.problems.append(f"{what}: module {mod} does not exist")
        elif attr and not self.resolves(mod, attr):
            self.problems.append(f"{what}: {mod} has no {attr}")

    def layer_check(self, layers: dict[str, str]) -> tuple[dict, list[str]]:
        """``(layer graph, violations)`` over runtime (module/function-level) edges."""
        graph: dict[str, set[str]] = {}
        violations: list[str] = []
        seen_exceptions: set[tuple[str, str]] = set()
        for m, info in self.info.items():
            src = layers[m]
            for kind in RUNTIME_KINDS:
                for t in info.imports[kind]:
                    dst = layers[t]
                    if dst != src:
                        graph.setdefault(src, set()).add(dst)
                    allowed = self.cfg.layer_rules.get(src)
                    if allowed is None or dst == src or dst in allowed:
                        continue
                    if (m, t) in self.cfg.layer_exceptions:
                        seen_exceptions.add((m, t))
                        continue
                    violations.append(f"{m} -> {t} ({src} -> {dst}, {kind})")
        for a, b in self.cfg.layer_exceptions:
            if (a, b) not in seen_exceptions:
                self.problems.append(
                    f"layer_exceptions: {a} -> {b} is not a rule-breaking edge "
                    "any more; remove it"
                )
        for layer, targets in self.cfg.layer_rules.items():
            for name in [layer, *targets]:
                if name not in set(layers.values()):
                    self.problems.append(f"layer_rules: no module has layer {name!r}")
        return {k: sorted(v) for k, v in sorted(graph.items())}, sorted(set(violations))

    def features(self) -> dict:
        path = self.cfg.features
        if path is None:
            self.notices.append("features: not configured; no features registry")
            return {}
        rel = self.cfg.rel(path)
        if not path.is_file():
            self.problems.append(f"{rel}: does not exist")
            return {}
        with path.open("rb") as fh:
            entries = tomllib.load(fh).get("feature", [])
        out = self._entries(rel, entries, FEATURE_KEYS, "id", "feature")
        for fid, f in out.items():
            where = f"{rel}: feature {fid}"
            if not FEATURE_ID.fullmatch(fid):
                self.problems.append(f"{where}: id must match {FEATURE_ID.pattern}")
            if not _one_line(f.get("purpose", "")):
                self.problems.append(f"{where}: purpose must be one non-empty line")
            if not f.get("modules"):
                self.problems.append(f"{where}: needs at least one module")
            for m in f.get("modules", []):
                if m not in self.mods:
                    self.problems.append(f"{where}: module {m} does not exist")
            for a in f.get("assets", []):
                if a not in self.assets:
                    self.problems.append(f"{where}: asset {a} is not a mapped asset")
            for s in f.get("symbols", []):
                mod, sep, name = s.partition(":")
                if not sep or not name:
                    self.problems.append(f"{where}: symbol {s!r} must be module:Name")
                elif mod not in self.mods:
                    self.problems.append(
                        f"{where}: symbol {s}: module {mod} does not exist"
                    )
                elif not self.resolves(mod, name):
                    self.problems.append(f"{where}: symbol {s}: {mod} has no {name}")
            for key in ("tests", "docs"):
                for ref in f.get(key, []):
                    err = self._path_ref(ref)
                    if err:
                        self.problems.append(f"{where}: {key} {ref}: {err}")
        return out

    def _entries(
        self, rel: str, items: list, keys: set[str], idkey: str, what: str
    ) -> dict[str, dict]:
        """``[[what]]`` tables keyed by *idkey*, lists sorted. Missing or
        duplicate ids and unknown keys are problems."""
        out: dict[str, dict] = {}
        for i, item in enumerate(items):
            ident = item.get(idkey, "")
            where = f"{rel}: {what} {ident or f'#{i}'}"
            if not ident:
                self.problems.append(f"{where}: needs {idkey!r}")
            if ident in out:
                self.problems.append(f"{where}: duplicate")
            for key in sorted(set(item) - keys):
                self.problems.append(f"{where}: unknown key {key!r}")
            out[ident] = {
                k: sorted(v) if isinstance(v, list) else v
                for k, v in item.items()
                if k != idkey
            }
        return dict(sorted(out.items()))

    def _ref_ok(self, ref: str) -> bool:
        """``module`` or ``module:Name`` names something mapped."""
        mod, sep, name = ref.partition(":")
        return mod in self.mods and (not sep or self.resolves(mod, name))

    def domain(self) -> dict:
        """Read, validate and normalise the domain charter (``domain.toml``)."""
        path = self.cfg.domain
        if path is None:
            self.notices.append(
                "domain: not configured; charter checks (depends_on, private "
                "imports) are off"
            )
            return {}
        rel = self.cfg.rel(path)
        if not path.is_file():
            self.problems.append(f"{rel}: does not exist")
            return {}
        with path.open("rb") as fh:
            raw = tomllib.load(fh)
        for key in sorted(set(raw) - DOMAIN_KEYS):
            self.problems.append(f"{rel}: unknown key {key!r}")
        sentence = raw.get("domain", "")
        if not _one_line(sentence):
            self.problems.append(f"{rel}: domain must be one non-empty sentence")
        for ref in raw.get("public_api", []):
            if not self._ref_ok(ref):
                self.problems.append(f"{rel}: public_api {ref}: does not exist")

        owns = self._entries(rel, raw.get("owns", []), OWNS_KEYS, "concept", "owns")
        for concept, entry in owns.items():
            if not entry.get("modules"):
                self.problems.append(
                    f"{rel}: owns {concept}: needs at least one module"
                )
            for ref in [*entry.get("modules", []), *entry.get("symbols", [])]:
                if not self._ref_ok(ref):
                    self.problems.append(f"{rel}: owns {concept}: {ref} does not exist")
        non_goals = self._entries(
            rel, raw.get("non_goals", []), NON_GOAL_KEYS, "concept", "non_goal"
        )
        for concept in set(owns) & set(non_goals):
            self.problems.append(f"{rel}: {concept} is both owned and a non-goal")
        depends = self._entries(
            rel, raw.get("depends_on", []), DEPENDS_KEYS, "distribution", "depends_on"
        )
        # ``imports`` (a top-level import name, or a list) maps imports to the
        # distribution, so usage is attributed to the declared distribution.
        for dist, entry in depends.items():
            names = entry.get("imports")
            names = [names] if isinstance(names, str) else names or []
            entry["imports"] = sorted(names)
            if not names:
                self.problems.append(f"{rel}: depends_on {dist}: needs 'imports'")
            for name in names:
                where = f"{rel}: depends_on {dist}: imports {name!r}"
                if not re.fullmatch(r"[A-Za-z_]\w*", name):
                    self.problems.append(f"{where} is not a top-level import name")
                elif name in self._import_dist:
                    other = self._import_dist[name]
                    self.problems.append(f"{where} is also claimed by {other}")
                else:
                    if self.cfg.distributions.get(name, dist) != dist:
                        self.problems.append(
                            f"{where} conflicts with [tool.codemap.distributions] "
                            f"({self.cfg.distributions[name]})"
                        )
                    # The charter wins, so one conflict is one problem.
                    self._import_dist[name] = dist
        law = raw.get("law", {})
        for key in sorted(set(law) - LAW_KEYS):
            self.problems.append(f"{rel}: law: unknown key {key!r}")
        if law and not (
            str(law.get("url", "")).startswith(("https://", "http://"))
            and law.get("concepts")
            and all(isinstance(c, str) and c for c in law["concepts"])
        ):
            self.problems.append(f"{rel}: law needs an http(s) url and concept ids")
        out = {
            "domain": sentence.strip(),
            "public_api": sorted(raw.get("public_api", [])),
            "owns": owns,
            "non_goals": non_goals,
            "depends_on": depends,
        }
        if law:
            out["law"] = {
                "url": law.get("url", ""),
                "concepts": sorted(law.get("concepts", [])),
            }
        return out

    def external_usage(self, charter: dict) -> tuple[dict, dict, list[str]]:
        """``(usage, coupling, non-goal warnings)``; charter breaches go to problems.

        * usage: distribution -> sorted foreign names used (``module:Name``,
          or a bare module when only the module object is used);
        * coupling (recorded, never failed): per distribution, import sites,
          importing modules, distinct names, hard coupling (``isinstance`` /
          ``issubclass`` against, or subclassing of, a foreign name) and port
          candidates (foreign names used in annotations that are never
          subclassed or isinstance-checked: a Protocol could stand in).
        """
        usage: dict[str, set[str]] = {}
        sites: dict[str, int] = {}
        importers: dict[str, set[str]] = {}
        hard: dict[str, set[tuple[str, str]]] = {}
        annotated: dict[str, set[str]] = {}
        users: dict[tuple[str, str], set[str]] = {}
        for m, info in self.info.items():
            for top, n in info.ext_sites.items():
                d = self.dist_of(top)
                sites[d] = sites.get(d, 0) + n
                importers.setdefault(d, set()).add(m)
            for ref in info.ext_used:
                d = self.dist_of(ref)
                usage.setdefault(d, set()).add(ref)
                users.setdefault((d, ref), set()).add(m)
            for ref, how in info.ext_hard:
                hard.setdefault(self.dist_of(ref), set()).add((ref, how))
            for ref in info.ext_annotated:
                annotated.setdefault(self.dist_of(ref), set()).add(ref)
        usage.pop("stdlib", None)
        coupling = {}
        for d in sorted(usage):
            hard_refs = {ref for ref, _ in hard.get(d, ())}
            coupling[d] = {
                "import_sites": sites.get(d, 0),
                "importing_modules": sorted(importers.get(d, ())),
                "distinct_names": len(usage[d]),
                "hard_coupling": sorted(
                    f"{how}({ref})" for ref, how in hard.get(d, ())
                ),
                "port_candidates": sorted(annotated.get(d, set()) - hard_refs),
            }

        if charter:
            declared = charter["depends_on"]
            for d, refs in sorted(usage.items()):
                allowed = set(declared.get(d, {}).get("names", []))
                for ref in sorted(refs):
                    mod, _, name = ref.partition(":")
                    where = ", ".join(sorted(users[(d, ref)]))
                    if self._private(mod, name):
                        self.problems.append(
                            f"private import: {ref} (from {d}) used by {where}"
                        )
                    if d not in declared:
                        self.problems.append(
                            f"undeclared dependency: {d} ({ref}) used by {where}; "
                            "add it to depends_on"
                        )
                    elif ref not in allowed and f"{mod}:*" not in allowed:
                        self.problems.append(
                            f"undeclared name: {ref} (from {d}) used by {where}; "
                            "add it to depends_on"
                        )
            imported_tops = {
                t.partition(".")[0]
                for i in self.info.values()
                for targets in i.external.values()
                for t in targets
            }
            for d, entry in declared.items():
                if d not in usage:
                    self.problems.append(
                        f"depends_on {d}: declared but never imported; remove it"
                    )
                    continue
                for name in entry.get("imports", []):
                    if name not in imported_tops:
                        self.problems.append(
                            f"depends_on {d}: imports {name!r} is never imported"
                        )
                for ref in entry.get("names", []):
                    if not ref.endswith(":*") and ref not in usage.get(d, set()):
                        self.problems.append(
                            f"depends_on {d}: {ref} is declared but unused; remove it"
                        )
        warnings = []
        for concept, entry in charter.get("non_goals", {}).items() if charter else []:
            words = {w.lower() for w in entry.get("keywords", [])}
            for m, info in sorted(self.info.items()):
                leaf = m.rpartition(".")[2]
                if words & set(_words(leaf)):
                    warnings.append(f"{concept}: {m}")
                for sym in info.symbols:
                    if words & set(_words(sym)):
                        warnings.append(f"{concept}: {m}:{sym}")
        return (
            {d: sorted(v) for d, v in sorted(usage.items())},
            coupling,
            sorted(set(warnings)),
        )

    @staticmethod
    def _private(mod: str, name: str) -> bool:
        parts = mod.split(".")[1:]
        if name.startswith("_") and not name.startswith("__"):
            return True
        return any(
            (p.startswith("_") and not p.startswith("__")) or p in PRIVATE_SEGMENTS
            for p in parts
        )

    def _path_ref(self, ref: str) -> str:
        """Validate ``path`` or ``path::Name[::method]``; '' when it exists."""
        rel, *nodes = ref.split("::")
        p = self.cfg.root / rel
        if not p.exists():
            return "does not exist"
        if not nodes:
            return ""
        if p.suffix != ".py" or not p.is_file():
            return "'::' needs a .py file"
        body = ast.parse(p.read_text(encoding="utf-8")).body
        for node in nodes:
            hit = next(
                (
                    st
                    for st in body
                    if isinstance(
                        st, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                    )
                    and st.name == node
                ),
                None,
            )
            if hit is None:
                return f"no {node}"
            body = hit.body if isinstance(hit, ast.ClassDef) else []
        return ""

    def citation_error(self, span: str) -> str | None:
        """None when *span* is not a package citation; '' when it resolves;
        else why not. Citations: a dotted module or symbol reached through a
        module, ``module:symbol``, or a path from an import root
        (``pkg/a.py``) or the repo root (``src/pkg/a.py``)."""
        span = span.strip()
        if "/" in span and re.fullmatch(r"[\w.\-/]+/?", span):
            head = span.partition("/")[0]
            for pkg in self.cfg.packages:
                if head == pkg.name:
                    return "" if (pkg.import_root / span).exists() else "no such path"
                prefix = self.cfg.rel(pkg.path)
                if span == prefix or span.startswith(prefix + "/"):
                    return "" if (self.cfg.root / span).exists() else "no such path"
            return None
        if not self._citation_re.fullmatch(span):
            return None
        mod, sep, name = span.partition(":")
        if sep:
            return "" if self.resolves(mod, name) else "no such module:symbol"
        if mod in self.mods:
            return ""
        home = mod.rpartition(".")[0]
        while home and home not in self.mods:
            home = home.rpartition(".")[0]
        rest = mod[len(home) + 1 :] if home else ""
        if home and self.resolves(home, rest):
            return ""
        return "no such module or symbol"

    def narrative(self) -> list[str]:
        """Every backticked package citation in the narrative docs must still
        exist (hard check). Returns the docs checked."""
        checked = []
        if not self.cfg.narrative:
            self.notices.append("narrative: not configured; no citation check")
        for rel in self.cfg.narrative:
            p = self.cfg.root / rel
            if not p.is_file():
                self.problems.append(f"narrative: {rel} does not exist")
                continue
            checked.append(rel)
            text = re.sub(
                r"(?ms)^\s*(```|~~~).*?^\s*\1", "", p.read_text(encoding="utf-8")
            )
            for span in sorted(set(re.findall(r"`([^`\n]+)`", text))):
                err = self.citation_error(span)
                if err:
                    self.problems.append(f"narrative: {rel}: `{span.strip()}`: {err}")
        return checked

    def claim_docs(self) -> list[Path]:
        cfg = self.cfg
        if not cfg.claims_docs:
            return []
        listed = tracked_files(cfg, cfg.claims_docs)
        if listed is None:
            listed = []
            for top in cfg.claims_docs:
                p = cfg.root / top
                listed += [p] if p.is_file() else _walk(p, (".md",))
        out = []
        for p in listed:
            rel = cfg.rel(p)
            if (
                p.suffix == ".md"
                and p.is_file()
                and rel not in cfg.self_files
                and not any(
                    rel == x or rel.startswith(x.rstrip("/") + "/")
                    for x in cfg.claims_exclude
                )
            ):
                out.append(p)
        return sorted(set(out))

    def doc_claims(
        self, entry_points: dict, features: dict, charter: dict, public_api: dict
    ) -> tuple[dict, dict]:
        """``({doc: [claim]}, findings)``: what the docs claim, resolved
        against the code (heuristic; recorded, never failed). See CODEMAP.md."""
        cfg = self.cfg
        roots = cfg.roots_pattern()
        dotted_re = re.compile(rf"(?<![\w./-])(?:{roots})(?:\.\w+)+(?::\w+(?:\.\w+)*)?")
        import_re = re.compile(
            rf"^\s*from\s+((?:{roots})(?:\.\w+)*)\s+import\s+\(?([\w\s,]+)"
        )
        scripts = sorted(entry_points["scripts"], key=len, reverse=True)
        commands = set().union(*(i.commands for i in self.info.values()))
        strings = set().union(*(i.strings for i in self.info.values()))
        defined = set().union(*(i.defined for i in self.info.values()))
        tables = set()
        for pyproject in {cfg.source, *cfg.projects}:
            if pyproject.is_file():
                with pyproject.open("rb") as fh:
                    stack = [("", tomllib.load(fh))]
                while stack:
                    prefix, table = stack.pop()
                    for k, v in table.items():
                        if isinstance(v, dict):
                            tables.add(f"{prefix}{k}")
                            stack.append((f"{prefix}{k}.", v))

        def cli(text: str) -> tuple[str, bool] | None:
            text = text.replace("\\|", "|").strip().removeprefix("$ ").strip()
            for script in scripts:
                if text == script or text.startswith(script + " "):
                    tokens = text[len(script) :].split()
                    if not tokens or not commands or tokens[0].startswith("-"):
                        return text, True
                    if len(tokens) > 1 and tokens[1] == "|":  # cmd | cmd | cmd
                        subs = tokens[0::2]
                    else:  # cmd, or cmd|cmd as one word
                        subs = tokens[0].split("|")
                    return text, all(w in commands for w in subs if w)
            return None

        claims: dict[str, dict] = {}
        corpus: dict[str, str] = {}
        docs = self.claim_docs()
        if not cfg.claims_docs:
            self.notices.append(
                "claims_docs: not configured; doc claims and findings are empty"
            )
        elif not docs:
            self.notices.append("claims_docs: no tracked .md file matched")
        for p in docs:
            rel = cfg.rel(p)
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            corpus[rel] = "\n".join(lines)
            found: dict[tuple[int, str, str], bool] = {}

            fence = ""
            for no, line in enumerate(lines, 1):
                m = FENCE.match(line)
                if m:
                    fence = "" if fence else m.group(1)
                    continue
                chunks = [line] if fence else re.findall(r"`([^`\n]+)`", line)
                for chunk in chunks:
                    span = chunk.strip()
                    if not fence:
                        err = self.citation_error(span)
                        if err is not None:
                            found[(no, "module", span)] = not err
                            continue
                    else:
                        im = import_re.match(chunk)
                        if im:
                            for name in re.split(r"[\s,]+", im.group(2)):
                                if name and name != "as":
                                    ref = f"{im.group(1)}:{name}"
                                    found[(no, "import", ref)] = self._ref_ok(ref)
                        for token in dotted_re.findall(chunk):
                            err = self.citation_error(token)
                            if err is not None:
                                found[(no, "module", token)] = not err
                    hit = cli(span)
                    if hit:
                        found[(no, "cli", hit[0])] = hit[1]
                    envs = (
                        re.findall(rf"(?:\$|\b)({ENV_NAME.pattern})(?==)", chunk)
                        + re.findall(
                            rf"environ(?:\.get)?\W+({ENV_NAME.pattern})", chunk
                        )
                        if fence
                        else (
                            [span.lstrip("$")]
                            if ENV_NAME.fullmatch(span.lstrip("$"))
                            else []
                        )
                    )
                    for env in envs:
                        found[(no, "env", env)] = env in strings or env in defined
                    for table in re.findall(r"\[(tool\.[\w.-]+)\]", chunk):
                        found[(no, "config", f"[{table}]")] = table in tables
            if found:
                # Shards hold no line numbers (they would churn on every doc
                # edit); ``--claims DOC`` prints them on demand.
                self.claim_lines[rel] = [
                    {"line": line, "kind": kind, "text": text, "resolved": ok}
                    for (line, kind, text), ok in sorted(found.items())
                ]
                unique = {(k, t): ok for (_, k, t), ok in found.items()}
                claims[rel] = {
                    "claims": [
                        {"kind": k, "text": t, "resolved": ok}
                        for (k, t), ok in sorted(unique.items())
                    ]
                }

        docs_ahead = sorted(
            {
                f"{rel}: {c['kind']} `{c['text']}`"
                for rel, cs in claims.items()
                for c in cs["claims"]
                if not c["resolved"]
            }
        )
        everything = "\n".join(corpus.values())

        def mentioned(name: str, text: str = everything) -> bool:
            return re.search(rf"(?<![\w]){re.escape(name)}(?![\w])", text) is not None

        code_ahead = set()
        if corpus:
            for pkg, api in public_api.items():
                for name in api or ():
                    if not mentioned(name):
                        code_ahead.add(f"public_api {pkg}:{name}")
            for ref in charter.get("public_api", []) if charter else []:
                if not mentioned(ref.rpartition(":")[2] or ref):
                    code_ahead.add(f"charter public_api {ref}")
            lines = everything.splitlines()
            for script in entry_points["scripts"]:
                if not mentioned(script):
                    code_ahead.add(f"script {script}")
                with_script = "\n".join(ln for ln in lines if mentioned(script, ln))
                for command in sorted(commands):
                    if not mentioned(command, with_script):
                        code_ahead.add(f"cli {script} {command}")
            for fid, f in features.items():
                text = "\n".join(
                    (cfg.root / d).read_text(encoding="utf-8", errors="replace")
                    for d in f.get("docs", [])
                    if (cfg.root / d).is_file()
                )
                mods = f.get("modules", [])
                names = [*mods, *(m.rpartition(".")[2] for m in mods)]
                names += [
                    s.rpartition(":")[2].split(".")[0] for s in f.get("symbols", [])
                ]
                if not any(mentioned(n, text) for n in names):
                    code_ahead.add(
                        f"feature {fid}: its docs name none of its modules or symbols"
                    )
        summary = {
            "docs": len(corpus),
            "claims": sum(len(c["claims"]) for c in claims.values()),
            "unresolved": sum(
                1 for cs in claims.values() for c in cs["claims"] if not c["resolved"]
            ),
        }
        return claims, {
            "summary": summary,
            "docs_ahead": docs_ahead,
            "code_ahead": sorted(code_ahead),
        }

    def build(self) -> dict:
        cfg = self.cfg
        charter = self.domain()  # first: depends_on ``imports`` feed dist_of
        mod_hits, asset_hits = self._consumer_index()
        imported_by: dict[str, dict[str, set[str]]] = {
            m: {k: set() for k in IMPORT_KINDS} for m in self.mods
        }
        for m, info in self.info.items():
            for kind, targets in info.imports.items():
                for t in targets:
                    imported_by[t][kind].add(m)

        layers = {m: layer_of(cfg, m) for m in self.mods}
        asset_layers = {
            a: (
                layer_of(cfg, a.rpartition("/")[0])
                if a.split("/")[0] in cfg.names
                else ""
            )
            for a in self.assets
        }
        unknown = sorted(
            n
            for n, layer in [*layers.items(), *asset_layers.items()]
            if layer == "unknown"
        )
        if unknown:
            raise SystemExit(
                "codemap: no layer for "
                + ", ".join(unknown)
                + "; add it to [tool.codemap.layers]"
            )

        public_api: dict[str, dict[str, str] | None] = {}
        exported: dict[str, list[str]] = {m: [] for m in self.mods}
        for pkg in sorted(cfg.public_packages):
            if pkg not in self.info:
                self.problems.append(f"public_api: package {pkg} is not mapped")
                continue
            if self.public_unknown(pkg):
                public_api[pkg] = None
                continue
            api = {n: self.defining_module(pkg, n) for n in self.public(pkg)}
            public_api[pkg] = api
            for n, home in api.items():
                if home in exported:
                    exported[home].append(f"{pkg}:{n}")

        features = self.features()
        owners: dict[str, set[str]] = {}
        for fid, f in features.items():
            for m in [*f.get("modules", []), *f.get("assets", [])]:
                owners.setdefault(m, set()).add(fid)

        modules = {}
        for m, info in sorted(self.info.items()):
            # An unreadable ``__all__`` makes the public API unknown (null),
            # never empty or guessed, for a module and (above) a package root.
            public = None if self.public_unknown(m) else self.public(m)
            symbols = {
                n: {**s, "public": None if public is None else n in public}
                for n, s in sorted(info.symbols.items())
            }
            modules[m] = {
                "path": cfg.rel(info.path),
                "layer": layers[m],
                "doc": _doc_line(info.tree),
                "is_public": not any(
                    part.startswith("_") and not part.startswith("__")
                    for part in m.split(".")
                ),
                "public": public,
                "exported_as": sorted(exported[m]),
                "symbols": symbols,
                "imports_internal": {k: sorted(v) for k, v in info.imports.items()},
                "imports_external": {
                    k: self._by_dist(v) for k, v in info.external.items()
                },
                "imported_by": {k: sorted(v) for k, v in imported_by[m].items()},
                "consumers": sorted(mod_hits[m]),
                "features": sorted(owners.get(m, ())),
            }

        assets = {}
        for a, p in sorted(self.assets.items()):
            bn = a.rpartition("/")[2]
            assets[a] = {
                "path": cfg.rel(p),
                "layer": asset_layers[a],
                "referenced_by": sorted(
                    m for m, i in self.info.items() if bn in i.text
                ),
                "consumers": sorted(asset_hits[a]),
                "features": sorted(owners.get(a, ())),
            }

        graph, violations = self.layer_check(layers)
        cycles = self.cycles()
        for c in cycles:
            if c not in cfg.allowed_cycles:
                self.problems.append(
                    f"cycle (module level, not in allowed_cycles): {' <-> '.join(c)}"
                )
        for c in cfg.allowed_cycles:
            if c not in cycles:
                self.problems.append(
                    f"allowed_cycles: {' <-> '.join(c)} no longer exists; remove it"
                )
        for v in violations:
            self.problems.append(f"layer violation: {v}")
        narrative = self.narrative()
        usage, coupling, non_goal_warnings = self.external_usage(charter)
        entry_points = self.entry_points()
        claims, doc_findings = self.doc_claims(
            entry_points, features, charter, public_api
        )

        return {
            "schema": SCHEMA,
            "generator": generator_identity(),
            "projects": [cfg.rel(p) for p in cfg.projects],
            "packages": {
                p.name: cfg.rel(p.path)
                for p in sorted(cfg.packages, key=lambda p: p.name)
            },
            "layers": dict(sorted(cfg.layers.items())),
            "layer_rules": {k: sorted(v) for k, v in sorted(cfg.layer_rules.items())},
            "layer_exceptions": sorted(f"{a} -> {b}" for a, b in cfg.layer_exceptions),
            "layer_graph": graph,
            "layer_violations": violations,
            "public_api": public_api,
            "entry_points": entry_points,
            "cycles_module_level": cycles,
            "features": features,
            "narrative_docs": narrative,
            "domain": charter,
            "external_usage": usage,
            "coupling": coupling,
            "non_goal_warnings": non_goal_warnings,
            "doc_claims": doc_findings,
            "claims": claims,
            "modules": modules,
            "assets": assets,
        }

    def _by_dist(self, names: set[str]) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for n in sorted(names):
            out.setdefault(self.dist_of(n), []).append(n)
        return out

    def cycles(self) -> list[list[str]]:
        """Tarjan SCCs (size > 1) over module-level edges only."""
        graph = {m: sorted(i.imports["module_level"]) for m, i in self.info.items()}
        index: dict[str, int] = {}
        low: dict[str, int] = {}
        stack: list[str] = []
        on: set[str] = set()
        out: list[list[str]] = []

        def visit(v: str) -> None:
            index[v] = low[v] = len(index)
            stack.append(v)
            on.add(v)
            for w in graph[v]:
                if w not in index:
                    visit(w)
                    low[v] = min(low[v], low[w])
                elif w in on:
                    low[v] = min(low[v], index[w])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                if len(comp) > 1:
                    out.append(sorted(comp))

        sys.setrecursionlimit(max(sys.getrecursionlimit(), 10 * len(graph) + 1000))
        for v in sorted(graph):
            if v not in index:
                visit(v)
        return sorted(out)


# --------------------------------------------------------------------- shards


def _one_line(text: str) -> bool:
    return bool(text.strip()) and "\n" not in text.strip()


def _words(identifier: str) -> list[str]:
    """``ChannelControl`` / ``intent_codec`` -> lower-case words."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", identifier)
    return [w.lower() for w in re.split(r"[\s_]+", spaced) if w]


def render(data: object) -> str:
    return json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def shard_name(key: str) -> str:
    """File name for a module (``pkg.a.b``) or asset (``pkg/a/x.js``) shard."""
    return key.replace("/", ".") + ".json"


INDEX_SECTIONS = (
    "schema",
    "generator",
    "packages",
    "projects",
    "layers",
    "layer_rules",
    "layer_exceptions",
    "layer_graph",
    "layer_violations",
    "public_api",
    "entry_points",
    "cycles_module_level",
    "features",
    "narrative_docs",
    "domain",
    "external_usage",
    "coupling",
    "non_goal_warnings",
    "doc_claims",
)


def shards(data: dict) -> dict[str, str]:
    """Split the map into ``{path relative to out_dir: text}``.

    ``index.json`` holds the repo-level sections and a name -> layer list;
    every module / asset gets its own small file so a change re-maps only the
    shards it touches.
    """
    index = {k: data[k] for k in INDEX_SECTIONS}
    index["modules"] = {m: e["layer"] for m, e in data["modules"].items()}
    index["assets"] = {a: e["layer"] for a, e in data["assets"].items()}
    out = {"index.json": render(index)}
    for section in ("modules", "assets", "claims"):
        for key, entry in data[section].items():
            out[f"{section}/{shard_name(key)}"] = render({key: entry})
    return out


def existing_shards(out_dir: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    if not out_dir.is_dir():
        return found
    for p in sorted(out_dir.rglob("*.json")):
        found[p.relative_to(out_dir).as_posix()] = p.read_text(encoding="utf-8")
    return found


def compare(expected: dict[str, str], out_dir: Path) -> tuple[list[str], list[str]]:
    """Return ``(stale, orphans)``: shards that are missing/different, and shards
    on disk that no module produces any more."""
    current = existing_shards(out_dir)
    stale = sorted(p for p, text in expected.items() if current.get(p) != text)
    orphans = sorted(set(current) - set(expected))
    return stale, orphans


def write(
    expected: dict[str, str], out_dir: Path, only_changed: bool = False
) -> list[str]:
    """Write shards (all, or only stale ones) and delete orphans. Returns the
    relative paths written or removed."""
    stale, orphans = compare(expected, out_dir)
    touched = []
    for rel in stale if only_changed else sorted(expected):
        p = out_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(expected[rel], encoding="utf-8")
        if rel in stale:
            touched.append(rel)
    for rel in orphans:
        (out_dir / rel).unlink()
        touched.append(rel)
    return sorted(touched)


def changed_fields(old_text: str | None, new_text: str) -> str:
    """Short ``(field, field)`` hint for a stale shard."""
    if old_text is None:
        return "(new)"
    try:
        old = json.loads(old_text)
    except json.JSONDecodeError:
        return "(unreadable)"
    new = json.loads(new_text)
    if len(old) == len(new) == 1 and set(old) == set(new):  # module / asset shard
        (key,) = new
        old, new = old[key], new[key]
    if not isinstance(old, dict) or not isinstance(new, dict):
        return "(content)"
    fields = sorted(f for f in set(old) | set(new) if old.get(f) != new.get(f))
    return f"({', '.join(fields)})" if fields else "(formatting only)"


def _report_problems(problems: list[str]) -> None:
    print(f"codemap: {len(problems)} problem(s):")
    for p in problems:
        print(f"  {p}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("--root", type=Path, default=SCRIPT.parents[1], help="repo root")
    ap.add_argument("--config", type=Path, help="pyproject.toml holding [tool.codemap]")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="fail on stale shards or broken references"
    )
    mode.add_argument(
        "--write-changed",
        action="store_true",
        help="rewrite only stale shards (and remove orphans)",
    )
    mode.add_argument(
        "--module", metavar="DOTTED", help="print one module (or asset path) entry"
    )
    mode.add_argument("--feature", metavar="ID", help="print one feature entry")
    mode.add_argument(
        "--claims", metavar="DOC", help="print one doc's claims with line numbers"
    )
    args = ap.parse_args(argv)

    cfg = load_config(args.root, args.config)
    cm = CodeMap(cfg)
    data = cm.build()

    if args.module:
        entry = data["modules"].get(args.module) or data["assets"].get(args.module)
        if entry is None:
            print(f"unknown module: {args.module}", file=sys.stderr)
            return 2
        # loc is shown here only: in a shard, every edit would churn it.
        loc = len((cfg.root / entry["path"]).read_text(encoding="utf-8").splitlines())
        print(
            json.dumps({args.module: {**entry, "loc": loc}}, indent=2, sort_keys=True)
        )
        return 0

    if args.claims:
        doc = Path(args.claims)
        if doc.is_absolute() and doc.is_relative_to(cfg.root):
            doc = doc.relative_to(cfg.root)
        key = Path(os.path.normpath(doc)).as_posix()
        found = cm.claim_lines.get(key)
        if found is None:
            print(f"no claims indexed for {args.claims}", file=sys.stderr)
            return 2
        print(json.dumps({key: found}, indent=2, sort_keys=True))
        return 0

    if args.feature:
        feature = data["features"].get(args.feature)
        if feature is None:
            known = ", ".join(data["features"]) or "none"
            print(f"unknown feature: {args.feature} (known: {known})", file=sys.stderr)
            return 2
        mods = {
            m: {
                k: data["modules"][m][k]
                for k in ("path", "layer", "doc", "public", "exported_as")
            }
            for m in feature.get("modules", [])
            if m in data["modules"]
        }
        print(
            json.dumps(
                {args.feature: {**feature, "module_map": mods}},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    expected = shards(data)
    where = cfg.rel(cfg.out_dir)
    for note in cm.notices:
        print(f"codemap: note: {note}")
    if data["non_goal_warnings"]:
        print(
            f"codemap: {len(data['non_goal_warnings'])} non-goal warning(s) "
            f"(index.json non_goal_warnings); review, do not silence"
        )
    if args.check:
        stale, orphans = compare(expected, cfg.out_dir)
        ok = not stale and not orphans and not cm.problems
        if not stale and not orphans:
            print(f"codemap up to date ({len(expected)} shards in {where})")
        else:
            current = existing_shards(cfg.out_dir)
            print(
                f"{where} is stale. Regenerate: "
                "python scripts/codemap.py --write-changed"
            )
            for rel in stale:
                print(
                    f"  stale:  {rel} {changed_fields(current.get(rel), expected[rel])}"
                )
            for rel in orphans:
                print(f"  orphan: {rel}")
        if cm.problems:
            _report_problems(cm.problems)
        return 0 if ok else 1

    touched = write(expected, cfg.out_dir, only_changed=args.write_changed)
    for rel in touched:
        print(f"  {'removed' if rel not in expected else 'wrote'} {where}/{rel}")
    print(f"codemap: {len(touched)} shard(s) changed, {len(expected)} total in {where}")
    if cm.problems:
        _report_problems(cm.problems)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
