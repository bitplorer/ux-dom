#!/usr/bin/env python3
"""Persisted, machine-readable map of ``src/ux_dom`` (stdlib only, AST-based).

Usage::

    python scripts/codemap.py                     # rewrite every shard, remove orphans
    python scripts/codemap.py --write-changed     # rewrite only stale shards (PR authors)
    python scripts/codemap.py --check             # exit 1, naming each stale shard
    python scripts/codemap.py --module ux_dom.x   # print one module's entry

The map is sharded under docs/internals/codemap/: ``index.json`` plus one
``modules/<dotted.name>.json`` per module and ``assets/<dotted.path>.json`` per
JS asset. Output is deterministic: sorted keys, sorted lists, no timestamps or
commit hashes, so a shard only changes when its module (or a reference to it)
does. See docs/internals/CODEMAP.md.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PKG = "ux_dom"
OUT_DIR = ROOT / "docs" / "internals" / "codemap"

# Module prefix -> layer (longest prefix wins; the root ``ux_dom`` matches only
# itself, and a module matching nothing fails the build). Extends the package
# ontology in AGENTS.md with layers it does not name: dom (tags / serialize), document (Document, contributions, runtime
# facades, package static), components (typed trees on top of dom), ui (optional
# kit), cli (pure-dom Typer CLI), integrations (HTTP / ASGI / IO adapters),
# support (shared helpers).
LAYERS: dict[str, str] = {
    "ux_dom": "root",
    "ux_dom.__main__": "cli",
    "ux_dom.alpinejs": "components",
    "ux_dom.cli": "cli",
    "ux_dom.compat": "support",
    "ux_dom.concurrency": "support",
    "ux_dom.diagnostics": "support",
    "ux_dom.dom": "dom",
    "ux_dom.elements": "components",
    "ux_dom.htmx": "integrations",
    "ux_dom.plugins": "document",
    "ux_dom.profiling": "support",
    "ux_dom.response": "integrations",
    "ux_dom.scripts": "document",
    "ux_dom.settings": "document",
    "ux_dom.slots": "components",
    "ux_dom.ui": "ui",
    "ux_dom.utils": "support",
    "ux_dom.web_io": "integrations",
}

# Where consumers live, and which file types are scanned there.
CONSUMER_DIRS: dict[str, tuple[str, ...]] = {
    "docs": (".md",),
    "examples": (".py", ".md", ".html", ".js", ".mjs"),
    "standalone": (".py", ".md", ".html", ".js", ".mjs"),
    "tests": (".py", ".md", ".html", ".js", ".mjs"),
}
# The map's own doc and test name modules only to describe the map; counting
# them would churn shards whenever an example or allowlist there changes.
SELF_FILES = {"docs/internals/CODEMAP.md", "tests/04_production/test_codemap.py"}
SKIP_DIRS = {
    "__pycache__",
    "node_modules",
    ".git",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
}

IMPORT_KINDS = ("module_level", "function_level", "type_checking")


def layer_of(name: str) -> str:
    """Layer for a dotted module name (or ``ux_dom/...`` asset path)."""
    dotted = name.replace("/", ".")
    best = ""
    for prefix in LAYERS:
        hit = dotted == prefix or (prefix != PKG and dotted.startswith(prefix + "."))
        if hit and len(prefix) > len(best):
            best = prefix
    return LAYERS.get(best, "unknown")


def _walk(base: Path, exts: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if fn.endswith(exts):
                out.append(Path(dirpath) / fn)
    return out


def consumer_files() -> list[Path]:
    """Git-tracked files under CONSUMER_DIRS (so untracked scratch files never
    change the map); falls back to walking the tree outside a git checkout."""
    try:
        listed = subprocess.run(
            ["git", "ls-files", "-z", "--", *sorted(CONSUMER_DIRS)],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout.decode("utf-8")
        paths = [ROOT / rel for rel in listed.split("\0") if rel]
    except (OSError, subprocess.CalledProcessError):
        paths = [p for top in sorted(CONSUMER_DIRS) for p in _walk(ROOT / top, ("",))]
    out = []
    for p in paths:
        rel = _rel(p)
        top = rel.partition("/")[0]
        if (
            top in CONSUMER_DIRS
            and p.name.endswith(CONSUMER_DIRS[top])
            and rel not in SELF_FILES
            and not SKIP_DIRS.intersection(p.parts)
            and p.is_file()
        ):
            out.append(p)
    return sorted(out)


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def discover() -> tuple[dict[str, Path], dict[str, Path]]:
    """Return ``({dotted module: path}, {asset key: path})``."""
    mods: dict[str, Path] = {}
    assets: dict[str, Path] = {}
    for p in _walk(SRC / PKG, (".py", ".js")):
        rel = p.relative_to(SRC).as_posix()
        if p.suffix == ".js":
            assets[rel] = p
            continue
        dotted = rel[:-3].replace("/", ".")
        if dotted.endswith(".__init__"):
            dotted = dotted[: -len(".__init__")]
        mods[dotted] = p
    return mods, assets


# --------------------------------------------------------------------------- AST


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


class ModuleInfo:
    def __init__(self, name: str, path: Path, mods: dict[str, Path]):
        self.name = name
        self.path = path
        self.is_pkg = path.name == "__init__.py"
        self.text = path.read_text(encoding="utf-8")
        self.tree = ast.parse(self.text)
        self.mods = mods
        self.imports: dict[str, set[str]] = {k: set() for k in IMPORT_KINDS}
        self.defined: set[str] = set()  # def / class / assignment targets
        self.aliases: dict[str, str] = {}  # X = Y (Y a bare name)
        self.from_imports: dict[str, tuple[str, str]] = (
            {}
        )  # local -> (module, original)
        self.reexports: set[str] = set()  # ``import x as x`` / ``from m import x as x``
        self.stars: list[str] = []  # internal modules star-imported at module level
        self.all: list[str] | None = None
        self._scan()

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

    def _targets(self, node: ast.Import | ast.ImportFrom) -> set[str]:
        out: set[str] = set()
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        else:
            base = self._base(node)
            names = [
                f"{base}.{a.name}" if f"{base}.{a.name}" in self.mods else base
                for a in node.names
            ]
        for n in names:
            if n == PKG or n.startswith(PKG + "."):
                t = self._longest_module(n)
                if t and t != self.name:
                    out.add(t)
        return out

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
                self.imports[kind] |= self._targets(n)

        for st in _top_level_stmts(self.tree.body):
            if id(st) in tc_ids:
                continue
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.defined.add(st.name)
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
                    and isinstance(st.value, ast.Name)
                ):
                    self.aliases[st.targets[0].id] = st.value.id
                if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
                    self._read_all(st)
            elif (
                isinstance(st, ast.Expr)
                and isinstance(st.value, ast.Call)
                and isinstance(st.value.func, ast.Attribute)
                and isinstance(st.value.func.value, ast.Name)
                and st.value.func.value.id == "__all__"
            ):
                raise self._bad_all(st, f"``__all__.{st.value.func.attr}(...)``")
            elif isinstance(st, ast.Import):
                for a in st.names:
                    if a.asname and a.asname == a.name.rpartition(".")[2]:
                        self.reexports.add(a.asname)
            elif isinstance(st, ast.ImportFrom):
                base = self._base(st)
                for a in st.names:
                    if a.name == "*":
                        star = self._longest_module(base)
                        if (
                            star
                            and star != self.name
                            and (base == PKG or base.startswith(PKG + "."))
                        ):
                            self.stars.append(star)
                        continue
                    local = a.asname or a.name
                    self.from_imports[local] = (base, a.name)
                    if a.asname == a.name:
                        self.reexports.add(local)

    def _bad_all(self, st: ast.stmt, why: str) -> SystemExit:
        where = _rel(self.path) if self.path.is_relative_to(ROOT) else self.path
        return SystemExit(
            f"codemap: {where}:{st.lineno}: {why}; ``__all__`` must be "
            "a literal list/tuple of strings (or drop it to use the derived "
            "public set)"
        )

    def _read_all(self, st: ast.stmt) -> None:
        """Read a literal ``__all__``; fail loudly on anything else.

        A computed ``__all__`` cannot be read statically, and silently guessing
        would record a wrong public surface in the shards.
        """
        value = getattr(st, "value", None)
        if not (
            isinstance(value, (ast.List, ast.Tuple))
            and all(
                isinstance(e, ast.Constant) and isinstance(e.value, str)
                for e in value.elts
            )
        ):
            raise self._bad_all(st, "non-literal ``__all__``")
        names = [e.value for e in value.elts]  # type: ignore[attr-defined]
        if isinstance(st, ast.AugAssign):
            if self.all is None:
                raise self._bad_all(st, "``__all__ +=`` before ``__all__ =``")
            names = self.all + names
        self.all = names


class CodeMap:
    def __init__(self) -> None:
        self.mods, self.assets = discover()
        self.info = {m: ModuleInfo(m, p, self.mods) for m, p in self.mods.items()}
        self._public: dict[str, list[str]] = {}

    def public(self, mod: str, _seen: frozenset[str] = frozenset()) -> list[str]:
        """``__all__`` if defined, else non-underscore defs/classes/assignments
        plus PEP 484 re-exports (``x as x``) and star-import expansions."""
        if mod in self._public:
            return self._public[mod]
        info = self.info[mod]
        if info.all is not None:
            names = set(info.all)
        else:
            names = {n for n in info.defined | info.reexports if not n.startswith("_")}
            for star in info.stars:
                if star not in _seen:
                    names |= set(self.public(star, _seen | {mod}))
        self._public[mod] = sorted(names)
        return self._public[mod]

    def defining_module(
        self, mod: str, name: str, _seen: frozenset[tuple[str, str]] = frozenset()
    ) -> str:
        """Follow re-exports / star imports / ``X = Y`` aliases to where *name* is defined."""
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

    # -- consumers
    def _consumer_index(self) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
        """Heuristic (cheap regex, documented in CODEMAP.md):

        * every dotted token ``ux_dom.a.b.c`` resolves to its longest known module
          prefix (so ``patch("ux_dom.cli.doctor.run")`` counts for ``ux_dom.cli.doctor``);
        * ``from ux_dom.a import b`` counts ``ux_dom.a.b`` when that is a module;
        * a symbol named through a re-exporting module (``from ux_dom import Htmx``,
          ``ux_dom.dom.div``) also counts for the module that defines it;
        * a path ``ux_dom/a/b.py`` counts for ``ux_dom.a.b``;
        * the bare root ``ux_dom`` counts only via ``import ux_dom`` / ``from ux_dom import``;
        * an asset counts when its file name (``x_element.js``) appears.
        """
        dotted_re = re.compile(r"(?<![\w.])ux_dom(?:\.[A-Za-z_]\w*)+")
        from_re = re.compile(
            r"from[ \t]+(ux_dom(?:\.\w+)*)[ \t]+import[ \t]*(?:\(([^)]*)\)|([^\n#;]*))"
        )
        root_re = re.compile(
            r"^\s*(?:import\s+ux_dom\b|from\s+ux_dom\s+import\b)", re.M
        )
        path_re = re.compile(r"(?<![\w.])ux_dom/((?:\w+/)*\w+)\.py\b")
        mod_hits: dict[str, set[str]] = {m: set() for m in self.mods}
        asset_hits: dict[str, set[str]] = {a: set() for a in self.assets}
        basenames = {a: a.rpartition("/")[2] for a in self.assets}

        def longest(dotted: str) -> str | None:
            while dotted and dotted != PKG:
                if dotted in self.mods:
                    return dotted
                dotted = dotted.rpartition(".")[0]
            return None

        def resolve(dotted: str) -> set[str]:
            """Module named by *dotted*, plus the defining module of a symbol
            accessed on it (``ux_dom.dom.div`` -> dom.src.htmltags)."""
            mod = longest(dotted) or PKG
            out = {mod} if mod != PKG else set()
            rest = dotted[len(mod) + 1 :].split(".")[0] if dotted != mod else ""
            home = self.symbol_home(mod, rest) if rest else None
            if home and home != PKG:
                out.add(home)
            return out

        for p in consumer_files():
            text = p.read_text(encoding="utf-8", errors="replace")
            rel = _rel(p)
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
                t = longest(PKG + "." + m.group(1).replace("/", "."))
                if t:
                    found.add(t)
            if root_re.search(text):
                found.add(PKG)
            for t in found:
                mod_hits[t].add(rel)
            for a, bn in basenames.items():
                if bn in text:
                    asset_hits[a].add(rel)
        return mod_hits, asset_hits

    def build(self) -> dict:
        mod_hits, asset_hits = self._consumer_index()
        imported_by: dict[str, dict[str, set[str]]] = {
            m: {k: set() for k in IMPORT_KINDS} for m in self.mods
        }
        for m, info in self.info.items():
            for kind, targets in info.imports.items():
                for t in targets:
                    imported_by[t][kind].add(m)

        unknown = sorted(
            n for n in [*self.mods, *self.assets] if layer_of(n) == "unknown"
        )
        if unknown:
            raise SystemExit(
                "codemap: no layer for " + ", ".join(unknown) + "; add it to LAYERS"
            )

        modules = {}
        for m, info in sorted(self.info.items()):
            modules[m] = {
                "path": _rel(info.path),
                "layer": layer_of(m),
                "public": self.public(m),
                "imports_internal": {k: sorted(v) for k, v in info.imports.items()},
                "imported_by": {k: sorted(v) for k, v in imported_by[m].items()},
                "consumers": sorted(mod_hits[m]),
            }

        assets = {}
        for a, p in sorted(self.assets.items()):
            bn = a.rpartition("/")[2]
            assets[a] = {
                "path": _rel(p),
                "layer": layer_of(a.rpartition("/")[0]),
                "referenced_by": sorted(
                    m for m, i in self.info.items() if bn in i.text
                ),
                "consumers": sorted(asset_hits[a]),
            }

        return {
            "schema": 1,
            "generator": "scripts/codemap.py",
            "layers": dict(sorted(LAYERS.items())),
            "public_api": {n: self.defining_module(PKG, n) for n in self.public(PKG)},
            "cycles_module_level": self.cycles(),
            "modules": modules,
            "assets": assets,
        }

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

        for v in sorted(graph):
            if v not in index:
                visit(v)
        return sorted(out)


def render(data: object) -> str:
    return json.dumps(data, indent=1, sort_keys=True) + "\n"


def shard_name(key: str) -> str:
    """File name for a module (``ux_dom.a.b``) or asset (``ux_dom/a/x.js``) shard."""
    return key.replace("/", ".") + ".json"


def shards(data: dict) -> dict[str, str]:
    """Split the map into ``{path relative to OUT_DIR: text}``.

    ``index.json`` holds the cross-cutting sections and a name -> layer list;
    every module / asset gets its own small file so a change re-maps only the
    shards it touches.
    """
    index = {
        "schema": data["schema"],
        "generator": data["generator"],
        "layers": data["layers"],
        "public_api": data["public_api"],
        "cycles_module_level": data["cycles_module_level"],
        "modules": {m: e["layer"] for m, e in data["modules"].items()},
        "assets": {a: e["layer"] for a, e in data["assets"].items()},
    }
    out = {"index.json": render(index)}
    for section in ("modules", "assets"):
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
    if not isinstance(old, dict):
        return ""
    fields = sorted(f for f in set(old) | set(new) if old.get(f) != new.get(f))
    return f"({', '.join(fields)})" if fields else "(formatting only)"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="fail, naming each stale shard"
    )
    mode.add_argument(
        "--write-changed",
        action="store_true",
        help="rewrite only stale shards (and remove orphans)",
    )
    mode.add_argument(
        "--module", metavar="DOTTED", help="print one module (or asset path) entry"
    )
    args = ap.parse_args(argv)

    data = CodeMap().build()

    if args.module:
        entry = data["modules"].get(args.module) or data["assets"].get(args.module)
        if entry is None:
            print(f"unknown module: {args.module}", file=sys.stderr)
            return 2
        # loc is shown here only: in a shard, every edit would churn it.
        loc = len((ROOT / entry["path"]).read_text(encoding="utf-8").splitlines())
        print(
            json.dumps({args.module: {**entry, "loc": loc}}, indent=2, sort_keys=True)
        )
        return 0

    expected = shards(data)
    where = _rel(OUT_DIR)
    if args.check:
        stale, orphans = compare(expected, OUT_DIR)
        if not stale and not orphans:
            print(f"codemap up to date ({len(expected)} shards in {where})")
            return 0
        current = existing_shards(OUT_DIR)
        print(
            f"{where} is stale. Regenerate: python scripts/codemap.py --write-changed"
        )
        for rel in stale:
            print(f"  stale:  {rel} {changed_fields(current.get(rel), expected[rel])}")
        for rel in orphans:
            print(f"  orphan: {rel}")
        return 1

    touched = write(expected, OUT_DIR, only_changed=args.write_changed)
    for rel in touched:
        print(f"  {'removed' if rel not in expected else 'wrote'} {where}/{rel}")
    print(f"codemap: {len(touched)} shard(s) changed, {len(expected)} total in {where}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
