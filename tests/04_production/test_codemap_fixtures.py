"""scripts/codemap.py is repo-agnostic: synthetic repos, one per layout.

Each fixture copies the generator to ``<tmp>/scripts/codemap.py`` (as a repo
vendoring it would), writes a tiny package plus ``[tool.codemap]`` config, and
runs it as a subprocess. Covered: src layout, flat layout, several package
roots without a root pyproject, a project in a subdirectory, and ``--check``
failing on broken feature / charter / narrative references, layer violations,
stale allowlists, cycles and undeclared or private foreign imports.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "codemap.py"


def make_repo(tmp: Path, files: dict[str, str]) -> Path:
    (tmp / "scripts").mkdir()
    shutil.copy(SCRIPT, tmp / "scripts" / "codemap.py")
    for rel, text in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
    return tmp


def run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "codemap.py"), *args],
        capture_output=True,
        text=True,
        cwd=repo,
    )


def index(repo: Path, out: str = "docs/internals/codemap") -> dict:
    return json.loads((repo / out / "index.json").read_text(encoding="utf-8"))


def shard(repo: Path, name: str, out: str = "docs/internals/codemap") -> dict:
    path = repo / out / "modules" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))[name]


SRC_LAYOUT = {
    "pyproject.toml": """
        [project]
        name = "alpha"
        [project.scripts]
        alpha = "alpha.cli:main"

        [tool.codemap]
        packages = ["src/alpha"]
        assets = ["src/alpha/**/*.js", "src/alpha/**/*.css"]
        features = "docs/features.toml"
        domain = "docs/domain.toml"
        narrative = ["docs/ARCH.md"]
        claims_docs = ["docs", "README.md"]
        claims_exclude = ["docs/old"]
        [tool.codemap.consumers]
        tests = [".py"]
        [tool.alpha]
        mode = "x"
        [tool.codemap.distributions]
        yaml = "PyYAML"
        [tool.codemap.layers]
        "alpha" = "root"
        "alpha.core" = "core"
        "alpha.cli" = "app"
        "alpha.web" = "app"
        "alpha.__main__" = "app"
        "alpha.static" = "app"
        [tool.codemap.layer_rules]
        core = []
        root = ["core"]
        """,
    "src/alpha/__init__.py": '''
        """Alpha package."""
        from alpha.core.engine import Engine as Engine
        __all__ = ["Engine"]
        ''',
    "src/alpha/core/__init__.py": "",
    "src/alpha/core/engine.py": '''
        """The engine."""
        import json
        import yaml
        from functools import lru_cache

        class Engine(dict):
            """Runs things.

            More text.
            """
            @lru_cache
            def run(self, n: int = 1) -> str:
                """Run once."""
                return json.dumps(yaml.safe_load(str(n)))

            async def _later(self, *a, key=None): ...

        def helper(x, /, y, *, z=2) -> int:
            return x
        ''',
    "src/alpha/cli.py": """
        import os
        from alpha.core.engine import Engine

        import argparse

        def main() -> None:
            argparse.ArgumentParser().add_subparsers().add_parser("go")
            os.environ.get("ALPHA_MODE")
            Engine().run()
        """,
    "src/alpha/__main__.py": "from alpha.cli import main\nmain()\n",
    "src/alpha/web.py": """
        from starlette.applications import Starlette
        app = Starlette()
        """,
    "src/alpha/static/app.js": "console.log(1)\n",
    "src/alpha/static/app.css": "body{}\n",
    "tests/test_engine.py": """
        from alpha import Engine

        class TestEngine:
            def test_run(self):
                assert Engine().run()
        """,
    "docs/ARCH.md": """
        The engine lives in `alpha.core.engine` (`alpha.core.engine:Engine.run`),
        see `alpha/core/engine.py` or `src/alpha/cli.py`. `alpha.Engine` is public.
        Prose like `not a module` and `other_pkg.x` is ignored.
        """,
    "README.md": """
        Run `alpha go` or `alpha nope`. Set `ALPHA_MODE` (or `ALPHA_GONE`).
        Configure `[tool.alpha]`.

        ```python
        from alpha import Engine, Missing
        alpha.core.engine.helper(1, 2)
        ```
        """,
    "docs/old/HISTORY.md": "`alpha.removed_long_ago`\n",
    "docs/features.toml": """
        [[feature]]
        id = "engine"
        purpose = "Run things."
        modules = ["alpha.core.engine"]
        symbols = ["alpha.core.engine:Engine.run", "alpha:Engine"]
        assets = ["alpha/static/app.js"]
        tests = ["tests/test_engine.py::TestEngine::test_run"]
        docs = ["docs/ARCH.md"]
        """,
    "docs/domain.toml": """
        domain = "alpha is the SSoT for engines."
        public_api = ["alpha:Engine"]
        [law]
        url = "https://example.com/spec"
        concepts = ["engine-run"]
        [[owns]]
        concept = "engines"
        modules = ["alpha.core.engine"]
        symbols = ["alpha:Engine"]
        [[non_goals]]
        concept = "web-serving"
        owner = "beta"
        keywords = ["web"]
        [[depends_on]]
        distribution = "PyYAML"
        imports = "yaml"
        names = ["yaml:safe_load"]
        [[depends_on]]
        distribution = "starlette"
        imports = "starlette"
        names = ["starlette.applications:Starlette"]
        """,
}


class TestLayouts(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_src_layout(self):
        repo = make_repo(self.tmp, SRC_LAYOUT)
        proc = run(repo)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(run(repo, "--check").returncode, 0)
        idx = index(repo)
        self.assertEqual(
            idx["generator"]["sha256"], hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
        )
        self.assertEqual(idx["public_api"], {"alpha": {"Engine": "alpha.core.engine"}})
        self.assertEqual(idx["entry_points"]["scripts"], {"alpha": "alpha.cli:main"})
        self.assertEqual(idx["entry_points"]["main_modules"], ["alpha.__main__"])
        self.assertEqual(idx["entry_points"]["asgi"], ["alpha.web:app"])
        self.assertEqual(
            sorted(idx["assets"]), ["alpha/static/app.css", "alpha/static/app.js"]
        )
        self.assertEqual(idx["features"]["engine"]["purpose"], "Run things.")
        self.assertEqual(idx["narrative_docs"], ["docs/ARCH.md"])
        self.assertEqual(idx["non_goal_warnings"], ["web-serving: alpha.web"])
        self.assertEqual(
            idx["coupling"]["PyYAML"]["hard_coupling"], []
        )  # recorded, never failed
        eng = shard(repo, "alpha.core.engine")
        self.assertEqual(eng["doc"], "The engine.")
        self.assertEqual(eng["features"], ["engine"])
        self.assertEqual(eng["exported_as"], ["alpha:Engine"])
        self.assertEqual(
            eng["imports_external"]["module_level"],
            {"PyYAML": ["yaml"], "stdlib": ["functools", "json"]},
        )
        cls = eng["symbols"]["Engine"]
        self.assertEqual(
            (cls["kind"], cls["doc"], cls["bases"]), ("class", "Runs things.", ["dict"])
        )
        run_ = cls["methods"]["run"]
        self.assertEqual(run_["signature"], "(self, n: int=1) -> str")
        self.assertEqual(run_["decorators"], ["lru_cache"])
        self.assertEqual(cls["methods"]["_later"]["kind"], "async function")
        self.assertEqual(
            eng["symbols"]["helper"]["signature"], "(x, /, y, *, z=2) -> int"
        )
        self.assertTrue(eng["symbols"]["helper"]["public"])  # no __all__: derived
        self.assertIn("tests/test_engine.py", eng["consumers"])
        self.assertIn("alpha.cli", eng["imported_by"]["module_level"])
        # Lookups
        proc = run(repo, "--feature", "engine")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('"module_map"', proc.stdout)
        self.assertEqual(run(repo, "--feature", "nope").returncode, 2)
        self.assertIn('"loc"', run(repo, "--module", "alpha.core.engine").stdout)

    def test_doc_claims_are_indexed_not_failed(self):
        repo = make_repo(self.tmp, SRC_LAYOUT)
        self.assertEqual(run(repo).returncode, 0)  # findings never fail
        claims = index(repo)["doc_claims"]
        self.assertEqual(
            claims["docs_ahead"],
            [
                "README.md: cli `alpha nope`",
                "README.md: env `ALPHA_GONE`",
                "README.md: import `alpha:Missing`",
            ],
        )
        self.assertEqual(claims["code_ahead"], [])
        readme = json.loads(
            (repo / "docs/internals/codemap/claims/README.md.json").read_text()
        )["README.md"]
        resolved = {(c["line"], c["kind"], c["text"]) for c in readme if c["resolved"]}
        self.assertEqual(
            resolved,
            {
                (1, "cli", "alpha go"),
                (1, "env", "ALPHA_MODE"),
                (2, "config", "[tool.alpha]"),
                (5, "import", "alpha:Engine"),
                (6, "module", "alpha.core.engine.helper"),
            },
        )
        self.assertFalse(
            (repo / "docs/internals/codemap/claims")
            .joinpath("docs.old.HISTORY.md.json")
            .exists()
        )  # claims_exclude
        self.assertEqual(
            index(repo)["domain"]["law"],
            {"url": "https://example.com/spec", "concepts": ["engine-run"]},
        )
        # Code ahead of docs: a public name no doc mentions.
        (repo / "src/alpha/__init__.py").write_text(
            "from alpha.core.engine import Engine as Engine\n\ndef undocumented(): ...\n"
        )
        run(repo)
        self.assertEqual(
            index(repo)["doc_claims"]["code_ahead"], ["public_api alpha:undocumented"]
        )

    def test_write_changed_only_touches_stale_shards(self):
        repo = make_repo(self.tmp, SRC_LAYOUT)
        run(repo)
        (repo / "src/alpha/cli.py").write_text(
            "from alpha.core.engine import helper\n\ndef main(): helper(1, 2)\n",
            encoding="utf-8",
        )
        self.assertEqual(run(repo, "--check").returncode, 1)
        proc = run(repo, "--write-changed")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("modules/alpha.cli.json", proc.stdout)
        self.assertNotIn("modules/alpha.web.json", proc.stdout)
        self.assertEqual(run(repo, "--check").returncode, 0)

    def test_flat_layout(self):
        repo = make_repo(
            self.tmp,
            {
                "pyproject.toml": """
                    [tool.codemap]
                    packages = ["flat"]
                    out_dir = "map"
                    """,
                "flat/__init__.py": "from .a import thing as thing\n",
                "flat/a.py": "def thing(): ...\n",
            },
        )
        proc = run(repo)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        idx = index(repo, "map")
        self.assertEqual(idx["modules"], {"flat": "", "flat.a": ""})
        self.assertEqual(idx["public_api"], {"flat": {"thing": "flat.a"}})
        self.assertEqual(run(repo, "--check").returncode, 0)

    def test_multiple_roots_without_root_pyproject(self):
        # cek-python shape: two distributions, config found one level down.
        repo = make_repo(
            self.tmp,
            {
                "host/pyproject.toml": """
                    [project.scripts]
                    hostcli = "host_pkg.cli:main"
                    [tool.codemap]
                    packages = ["host/src/host_pkg", "surface/src/surface_pkg"]
                    projects = ["host/pyproject.toml", "surface/pyproject.toml"]
                    """,
                "surface/pyproject.toml": """
                    [project.scripts]
                    surf = "surface_pkg:run"
                    """,
                "host/src/host_pkg/__init__.py": "",
                "host/src/host_pkg/cli.py": "def main(): ...\n",
                "surface/src/surface_pkg/__init__.py": (
                    "from host_pkg.cli import main\n\ndef run(): main()\n"
                ),
            },
        )
        proc = run(repo)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        idx = index(repo)
        self.assertEqual(sorted(idx["packages"]), ["host_pkg", "surface_pkg"])
        self.assertEqual(
            idx["entry_points"]["scripts"],
            {"hostcli": "host_pkg.cli:main", "surf": "surface_pkg:run"},
        )
        surf = shard(repo, "surface_pkg")
        self.assertEqual(surf["imports_internal"]["module_level"], ["host_pkg.cli"])
        self.assertEqual(surf["imports_external"]["module_level"], {})

    def test_project_in_subdirectory(self):
        # ux-channel shape: pyproject in python/, map at the repo root.
        repo = make_repo(
            self.tmp,
            {
                "python/pyproject.toml": """
                    [tool.poetry.scripts]
                    sub = "sub_pkg.cli:main"
                    [tool.codemap]
                    packages = ["python/src/sub_pkg"]
                    [tool.codemap.consumers]
                    "python/tests" = [".py"]
                    """,
                "python/src/sub_pkg/__init__.py": "",
                "python/src/sub_pkg/cli.py": "def main(): ...\n",
                "python/tests/test_cli.py": "import sub_pkg.cli\n",
            },
        )
        proc = run(repo)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(
            shard(repo, "sub_pkg.cli")["consumers"], ["python/tests/test_cli.py"]
        )
        self.assertEqual(
            index(repo)["entry_points"]["scripts"], {"sub": "sub_pkg.cli:main"}
        )


class TestCheckFailures(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = make_repo(Path(self._tmp.name), SRC_LAYOUT)
        self.assertEqual(run(self.repo).returncode, 0)

    def tearDown(self):
        self._tmp.cleanup()

    def edit(self, rel: str, old: str, new: str) -> None:
        p = self.repo / rel
        text = p.read_text(encoding="utf-8")
        self.assertIn(old, text)
        p.write_text(text.replace(old, new), encoding="utf-8")

    def check_fails_with(self, *needles: str) -> None:
        run(self.repo, "--write-changed")  # shards fresh: only problems remain
        proc = run(self.repo, "--check")
        self.assertEqual(proc.returncode, 1, proc.stdout)
        for needle in needles:
            self.assertIn(needle, proc.stdout)

    def test_broken_feature_references(self):
        self.edit(
            "docs/features.toml",
            'symbols = ["alpha.core.engine:Engine.run", "alpha:Engine"]',
            'symbols = ["alpha.core.engine:Engine.walk", "alpha:Gone", "alpha.nope:X"]\n'
            "modules2 = []",
        )
        self.edit("docs/features.toml", '"alpha.core.engine"]', '"alpha.core.gone"]')
        self.edit("docs/features.toml", "::test_run", "::test_missing")
        self.edit(
            "docs/features.toml", 'docs = ["docs/ARCH.md"]', 'docs = ["docs/NOPE.md"]'
        )
        self.check_fails_with(
            "module alpha.core.gone does not exist",
            "alpha.core.engine has no Engine.walk",
            "alpha has no Gone",
            "module alpha.nope does not exist",
            "unknown key 'modules2'",
            "tests tests/test_engine.py::TestEngine::test_missing: no test_missing",
            "docs docs/NOPE.md: does not exist",
        )

    def test_broken_narrative_citations(self):
        self.edit(
            "docs/ARCH.md",
            "`alpha.core.engine:Engine.run`",
            "`alpha.core.engine:Engine.fly`",
        )
        self.edit("docs/ARCH.md", "`src/alpha/cli.py`", "`src/alpha/gone.py`")
        self.edit("docs/ARCH.md", "`alpha.Engine`", "`alpha.Motor`")
        self.check_fails_with(
            "`alpha.core.engine:Engine.fly`: no such module:symbol",
            "`src/alpha/gone.py`: no such path",
            "`alpha.Motor`: no such module or symbol",
        )

    def test_broken_entry_point(self):
        self.edit(
            "pyproject.toml", 'alpha = "alpha.cli:main"', 'alpha = "alpha.cli:mian"'
        )
        self.check_fails_with("entry point scripts.alpha: alpha.cli has no mian")

    def test_layer_violation_and_exception(self):
        self.edit(
            "src/alpha/core/engine.py",
            "import json\n",
            "import json\nfrom alpha import cli\n",
        )
        self.check_fails_with(
            "layer violation: alpha.core.engine -> alpha.cli (core -> app, module_level)"
        )
        # An accepted exception silences it; a stale one is reported.
        self.edit(
            "pyproject.toml",
            "[tool.codemap.consumers]",
            'layer_exceptions = ["alpha.core.engine -> alpha.cli"]\n'
            "[tool.codemap.consumers]",
        )
        self.assertNotIn("layer violation", run(self.repo, "--check").stdout)
        self.edit("src/alpha/core/engine.py", "from alpha import cli\n", "")
        self.check_fails_with(
            "alpha.core.engine -> alpha.cli is not a rule-breaking edge"
        )

    def test_cycles_must_be_allowlisted(self):
        self.edit(
            "src/alpha/core/engine.py",
            "import json\n",
            "import json\nimport alpha.cli\n",
        )
        self.edit("pyproject.toml", "core = []", 'core = ["app"]')
        self.check_fails_with(
            "cycle (module level, not in allowed_cycles): alpha.cli <-> alpha.core.engine"
        )

    def test_charter_breaches(self):
        self.edit(
            "src/alpha/core/engine.py",
            "import yaml\n",
            "import yaml\nimport requests\nfrom yaml._private import x\n",
        )
        self.edit(
            "docs/domain.toml", 'symbols = ["alpha:Engine"]', 'symbols = ["alpha:Nope"]'
        )
        self.edit(
            "docs/domain.toml",
            'names = ["yaml:safe_load"]',
            'names = ["yaml:safe_load", "yaml:dump"]',
        )
        self.check_fails_with(
            "owns engines: alpha:Nope does not exist",
            "undeclared dependency: requests (requests) used by alpha.core.engine",
            "private import: yaml._private:x (from PyYAML)",
            "undeclared name: yaml._private:x (from PyYAML)",
            "depends_on PyYAML: yaml:dump is declared but unused",
        )

    def test_hard_coupling_is_recorded(self):
        self.edit(
            "src/alpha/core/engine.py",
            "def helper(",
            "class Loader(yaml.SafeLoader): ...\n\n"
            "def check(v: yaml.Node) -> bool:\n    return isinstance(v, yaml.YAMLObject)\n\n"
            "def helper(",
        )
        self.edit(
            "docs/domain.toml",
            'names = ["yaml:safe_load"]',
            'names = ["yaml:safe_load", "yaml:SafeLoader", "yaml:Node", "yaml:YAMLObject"]',
        )
        proc = run(self.repo, "--write-changed")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        coupling = index(self.repo)["coupling"]["PyYAML"]
        self.assertEqual(
            coupling["hard_coupling"],
            [
                "isinstance alpha.core.engine(yaml:YAMLObject)",
                "subclass alpha.core.engine.Loader(yaml:SafeLoader)",
            ],
        )
        self.assertEqual(coupling["port_candidates"], ["yaml:Node"])
        self.assertEqual(coupling["distinct_names"], 4)


if __name__ == "__main__":
    unittest.main()
