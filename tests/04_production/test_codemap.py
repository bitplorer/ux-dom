"""Persisted code map (docs/internals/codemap/) stays fresh, deterministic, and lawful."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codemap.py"

# Known module-level cycle, tracked as ledger item E4 in
# https://github.com/bitplorer/ux-dom/issues/59 (``allowed_cycles`` in
# pyproject.toml). Remove from both once broken.
KNOWN_CYCLES = [["ux_dom.dom.src.dom_tag", "ux_dom.dom.src.utils.dom_util"]]


def _load():
    spec = importlib.util.spec_from_file_location("_codemap", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses resolve their module by name
    spec.loader.exec_module(mod)
    return mod


def _run(*args, env=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )


class TestCodeMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codemap = _load()
        cls.cfg = cls.codemap.load_config(ROOT)
        cls.cm = cls.codemap.CodeMap(cls.cfg)
        cls.data = cls.cm.build()

    def test_committed_shards_are_fresh(self):
        proc = _run("--check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_deterministic_across_hash_seeds(self):
        again = self.codemap.CodeMap(self.cfg).build()
        self.assertEqual(self.codemap.shards(self.data), self.codemap.shards(again))
        for seed in ("1", "12345"):
            proc = _run("--check", env={**os.environ, "PYTHONHASHSEED": seed})
            self.assertEqual(proc.returncode, 0, f"seed {seed}: {proc.stdout}")

    def test_map_has_no_problems(self):
        # Broken feature/charter/narrative references, layer violations and
        # cycles outside ``allowed_cycles`` all land here (and fail --check).
        self.assertEqual(self.cm.problems, [])

    def test_no_new_module_level_cycles(self):
        self.assertEqual(self.data["cycles_module_level"], KNOWN_CYCLES)
        self.assertEqual(self.cfg.allowed_cycles, KNOWN_CYCLES)

    def test_dom_layer_imports_only_dom_and_support(self):
        # Ledger E9 (#59), now ``layer_rules.dom`` in pyproject.toml: the dom
        # layer may import only dom and support, at module or function level.
        self.assertEqual(self.cfg.layer_rules["dom"], ["support"])
        self.assertFalse(
            [e for e in self.cfg.layer_exceptions if e[0].startswith("ux_dom.dom.")]
        )
        layers = {m: e["layer"] for m, e in self.data["modules"].items()}
        bad = [
            f"{name} -> {target} ({kind})"
            for name, entry in self.data["modules"].items()
            if entry["layer"] == "dom"
            for kind in ("module_level", "function_level")
            for target in entry["imports_internal"][kind]
            if layers[target] not in {"dom", "support"}
        ]
        self.assertEqual(bad, [], "dom layer imports outside dom/support")
        self.assertEqual(self.data["layer_violations"], [])

    def test_index_names_the_generator(self):
        import hashlib

        gen = json.loads((self.cfg.out_dir / "index.json").read_text())["generator"]
        self.assertEqual(gen["sha256"], hashlib.sha256(SCRIPT.read_bytes()).hexdigest())
        self.assertEqual(gen["version"], self.codemap.VERSION)

    def test_features_and_charter_are_folded_in(self):
        self.assertIn("sanitizer", self.data["features"])
        shard = self.data["modules"]["ux_dom.dom.src.html_string"]
        self.assertIn("sanitizer", shard["features"])
        self.assertIn("html-sanitization", self.data["domain"]["owns"])
        self.assertIn("ux-valio", self.data["external_usage"])
        proc = _run("--feature", "csp")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ux_dom.plugins.csp", proc.stdout)

    def test_shards_carry_no_loc(self):
        # loc churns on every edit, so concurrent PRs on one module would conflict.
        for rel, text in self.codemap.shards(self.data).items():
            self.assertNotIn('"loc"', text, rel)
        proc = _run("--module", "ux_dom.cli.doctor")
        self.assertIn('"loc"', proc.stdout)  # still available on demand

    def test_consumers_follow_reexports_to_defining_module(self):
        mods = self.data["modules"]
        # ``from ux_dom import Htmx`` -> plugins.control.htmx defines Htmx.
        self.assertIn(
            "tests/02_document_plugins/test_document_runtimes_create.py",
            mods["ux_dom.plugins.control.htmx"]["consumers"],
        )
        # ``from ux_dom.dom import div`` -> dom.src.htmltags defines the tags.
        self.assertGreater(len(mods["ux_dom.dom.src.htmltags"]["consumers"]), 50)

    def test_every_module_has_a_known_layer(self):
        layer_of = self.codemap.layer_of
        self.assertEqual(layer_of(self.cfg, "ux_dom"), "root")
        self.assertEqual(layer_of(self.cfg, "ux_dom.newpkg.mod"), "unknown")
        names = [*self.data["modules"], *self.data["assets"]]
        unknown = [n for n in names if layer_of(self.cfg, n) == "unknown"]
        self.assertEqual(unknown, [])
        cfg = self.codemap.load_config(ROOT)
        del cfg.layers["ux_dom.web_io"]
        with self.assertRaises(SystemExit) as ctx:
            self.codemap.CodeMap(cfg).build()
        self.assertIn("ux_dom.web_io", str(ctx.exception))

    def test_untracked_files_are_not_consumers(self):
        scratch = ROOT / "tests" / "_codemap_untracked_scratch.py"
        scratch.write_text("import ux_dom.cli\n", encoding="utf-8")
        try:
            files = self.codemap.consumer_files(self.cfg)
            self.assertNotIn(scratch, files)
            self.assertIn(Path(__file__).resolve().parent / "__init__.py", files)
        finally:
            scratch.unlink()

    def test_git_failure_inside_a_checkout_is_not_swallowed(self):
        # Falling back to a walk would silently count untracked files.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".git").write_text("not a repository\n", encoding="utf-8")
            cfg = self.codemap.load_config(ROOT)
            cfg.root = Path(tmp)
            with self.assertRaises(subprocess.CalledProcessError):
                self.codemap.tracked_files(cfg, ["tests"])
            (Path(tmp) / ".git").unlink()
            self.assertIsNone(self.codemap.tracked_files(cfg, ["tests"]))

    def test_only_if_type_checking_body_is_type_only(self):
        src = textwrap.dedent("""
            import typing
            from typing import TYPE_CHECKING
            if TYPE_CHECKING:
                import ux_dom.a
            else:
                import ux_dom.b
            if not TYPE_CHECKING:
                import ux_dom.c
            if typing.TYPE_CHECKING:
                import ux_dom.d
            """)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.py"
            path.write_text(src, encoding="utf-8")
            mods = {f"ux_dom.{n}": path for n in "abcdm"}
            info = self.codemap.ModuleInfo("ux_dom.m", path, mods, {"ux_dom"})
        self.assertEqual(info.imports["type_checking"], {"ux_dom.a", "ux_dom.d"})
        self.assertEqual(info.imports["module_level"], {"ux_dom.b", "ux_dom.c"})

    def _info(self, src: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.py"
            path.write_text(textwrap.dedent(src), encoding="utf-8")
            return self.codemap.ModuleInfo(
                "ux_dom.m", path, {"ux_dom.m": path}, {"ux_dom"}
            )

    def test_literal_all_is_read(self):
        info = self._info("""
            __all__ = ["a", "b"]
            __all__ += ("c",)
            """)
        self.assertEqual(info.all, ["a", "b", "c"])

    def test_non_literal_all_is_a_finding_not_a_crash(self):
        bad = {
            "comprehension": "__all__ = [n for n in globals() if n[0] != '_']",
            "concatenation": "__all__ = ['a'] + other.__all__",
            "name": "__all__ = NAMES",
            "non-string": "__all__ = ['a', 1]",
            "append": "__all__ = ['a']\n__all__.append('b')",
            "extend": "__all__ = ['a']\n__all__.extend(['b'])",
            "augassign-first": "__all__ += ['a']",
        }
        for label, src in bad.items():
            with self.subTest(label):
                info = self._info(src)  # no SystemExit
                (msg,) = info.all_errors
                self.assertRegex(msg, r"m\.py:\d+: ")
                self.assertIn("must be a literal list/tuple of strings", msg)

    def test_doc_edit_without_claim_change_keeps_map_fresh(self):
        # Claims shards carry no line numbers: a blank line must not go stale.
        doc = ROOT / "INSTALL.md"
        original = doc.read_bytes()
        try:
            doc.write_bytes(b"\n" + original)
            proc = _run("--check")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        finally:
            doc.write_bytes(original)
        lines = json.loads(_run("--claims", "INSTALL.md").stdout)["INSTALL.md"]
        self.assertTrue(all("line" in c for c in lines))  # on demand only
        for rel, text in self.codemap.shards(self.data).items():
            if rel.startswith("claims/"):
                self.assertNotIn('"line"', text, rel)

    def test_write_changed_is_surgical_and_removes_orphans(self):
        cm = self.codemap
        expected = cm.shards(self.data)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.assertEqual(sorted(cm.write(expected, out)), sorted(expected))
            self.assertEqual(cm.compare(expected, out), ([], []))

            edited = "modules/ux_dom.dom.json"
            (out / edited).write_text("{}\n", encoding="utf-8")
            orphan = "modules/ux_dom.deleted_module.json"
            (out / orphan).write_text("{}\n", encoding="utf-8")
            self.assertEqual(cm.compare(expected, out), ([edited], [orphan]))

            self.assertEqual(
                cm.write(expected, out, only_changed=True), sorted([edited, orphan])
            )
            self.assertFalse((out / orphan).exists())
            self.assertEqual(cm.compare(expected, out), ([], []))

            (out / orphan).write_text("{}\n", encoding="utf-8")
            self.assertEqual(cm.write(expected, out), [orphan])  # full write too
            self.assertFalse((out / orphan).exists())
            json.loads((out / "index.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
