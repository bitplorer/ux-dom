"""uxdom build + deploy prepare."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import ScaffoldOptions, create_app
from ux_dom.cli.build import run_build

try:
    from ux_dom.cli.deploy import prepare_deploy
except ImportError:  # product deploy lives on uxcompose
    prepare_deploy = None


def _require_deploy():
    if prepare_deploy is None:
        raise unittest.SkipTest("product deploy is uxcompose, not uxdom")


class TestBuild(unittest.TestCase):
    def test_build_minimal_skip_tailwind(self):
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions(
                    "bapp",
                    dest=Path(td) / "bapp",
                    force=True,
                    template="minimal",
                    with_tailwind=False,
                )
            )
            # import needs deps — skip_import if heavy; try full
            rep = run_build(cwd=root, skip_tailwind=True, skip_import=False)
            self.assertTrue(any(s.name == "app/main.py" and s.ok for s in rep.steps))
            self.assertTrue(any(s.name == "x_element.js" and s.ok for s in rep.steps))
            imp = next(s for s in rep.steps if s.name.startswith("import"))
            self.assertTrue(imp.ok, imp.detail)
            self.assertTrue(rep.ok, rep.steps)


class TestDeploy(unittest.TestCase):
    def test_docker_files(self):
        _require_deploy()
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions("dapp", dest=Path(td) / "dapp", force=True)
            )
            res = prepare_deploy("docker", cwd=root, force=True)
            self.assertIn("Dockerfile", res.files_written)
            self.assertTrue((root / "Dockerfile").is_file())
            self.assertIn("uvicorn", (root / "Dockerfile").read_text())

    def test_checklist_no_files(self):
        _require_deploy()
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions("capp", dest=Path(td) / "capp", force=True)
            )
            res = prepare_deploy("checklist", cwd=root)
            self.assertEqual(res.files_written, [])
            self.assertTrue(any("uxdom build" in i for i in res.instructions))

    def test_fly_and_vps(self):
        _require_deploy()
        with TemporaryDirectory() as td:
            root = create_app(
                ScaffoldOptions("fapp", dest=Path(td) / "fapp", force=True)
            )
            fly = prepare_deploy("fly", cwd=root, force=True, app_name="fapp")
            self.assertTrue((root / "fly.toml").is_file())
            vps = prepare_deploy("vps", cwd=root, force=True, app_name="fapp")
            self.assertTrue(any("deploy/" in f for f in vps.files_written))


if __name__ == "__main__":
    unittest.main()
