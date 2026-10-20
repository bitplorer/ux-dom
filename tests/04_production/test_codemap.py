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
# https://github.com/bitplorer/ux-dom/issues/59. Remove once broken.
KNOWN_CYCLES = [["ux_dom.dom.src.dom_tag", "ux_dom.dom.src.utils.dom_util"]]

# Ledger E9 guard (#59): the dom layer may import only these layers, at module
# or function level. No exceptions exist today; add any as
# ``("ux_dom.dom.x", "ux_dom.y")  # <ledger id>: reason``.
DOM_ALLOWED_LAYERS = {"dom", "support"}
DOM_ALLOWED_EXCEPTIONS: set[tuple[str, str]] = set()


def _load():
    spec = importlib.util.spec_from_file_location("_codemap", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
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
        cls.data = cls.codemap.CodeMap().build()

    def test_committed_shards_are_fresh(self):
        proc = _run("--check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_deterministic_across_hash_seeds(self):
        again = self.codemap.CodeMap().build()
        self.assertEqual(self.codemap.shards(self.data), self.codemap.shards(again))
        for seed in ("1", "12345"):
            proc = _run("--check", env={**os.environ, "PYTHONHASHSEED": seed})
            self.assertEqual(proc.returncode, 0, f"seed {seed}: {proc.stdout}")

    def test_no_new_module_level_cycles(self):
        self.assertEqual(self.data["cycles_module_level"], KNOWN_CYCLES)

    def test_dom_layer_imports_only_dom_and_support(self):
        layers = {m: e["layer"] for m, e in self.data["modules"].items()}
        bad = [
            f"{name} -> {target} ({kind})"
            for name, entry in self.data["modules"].items()
            if entry["layer"] == "dom"
            for kind in ("module_level", "function_level")
            for target in entry["imports_internal"][kind]
            if layers[target] not in DOM_ALLOWED_LAYERS
            and (name, target) not in DOM_ALLOWED_EXCEPTIONS
        ]
        self.assertEqual(bad, [], "dom layer imports outside dom/support")

    def test_shards_carry_no_loc(self):
        # loc churns on every edit, so concurrent PRs on one module would conflict.
        for rel, text in self.codemap.shards(self.data).items():
            self.assertNotIn('"loc"', text, rel)
        proc = _run("--module", "ux_dom.cli.doctor")
        self.assertIn('"loc"', proc.stdout)  # still available on demand

    def test_consumers_follow_reexports_to_defining_module(self):
        mods = self.data["modules"]
        # ``from ux_dom.runtime import Htmx`` -> plugins.control.htmx defines Htmx.
        self.assertIn(
            "tests/02_document_plugins/test_document_runtimes_create.py",
            mods["ux_dom.plugins.control.htmx"]["consumers"],
        )
        # ``from ux_dom.dom import div`` -> dom.src.htmltags defines the tags.
        self.assertGreater(len(mods["ux_dom.dom.src.htmltags"]["consumers"]), 50)

    def test_every_module_has_a_known_layer(self):
        self.assertEqual(self.codemap.layer_of("ux_dom"), "root")
        self.assertEqual(self.codemap.layer_of("ux_dom.newpkg.mod"), "unknown")
        names = [*self.data["modules"], *self.data["assets"]]
        unknown = [n for n in names if self.codemap.layer_of(n) == "unknown"]
        self.assertEqual(unknown, [])
        saved = dict(self.codemap.LAYERS)
        try:
            del self.codemap.LAYERS["ux_dom.web_io"]
            with self.assertRaises(SystemExit) as ctx:
                self.codemap.CodeMap().build()
            self.assertIn("ux_dom.web_io", str(ctx.exception))
        finally:
            self.codemap.LAYERS.clear()
            self.codemap.LAYERS.update(saved)

    def test_untracked_files_are_not_consumers(self):
        scratch = ROOT / "tests" / "_codemap_untracked_scratch.py"
        scratch.write_text("import ux_dom.cli\n", encoding="utf-8")
        try:
            files = self.codemap.consumer_files()
            self.assertNotIn(scratch, files)
            self.assertIn(Path(__file__).resolve().parent / "__init__.py", files)
        finally:
            scratch.unlink()

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
            info = self.codemap.ModuleInfo("ux_dom.m", path, mods)
        self.assertEqual(info.imports["type_checking"], {"ux_dom.a", "ux_dom.d"})
        self.assertEqual(info.imports["module_level"], {"ux_dom.b", "ux_dom.c"})

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
