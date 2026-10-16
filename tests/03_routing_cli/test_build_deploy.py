"""uxdom build + deploy prepare."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import ScaffoldOptions, create_app
from ux_dom.cli.build import run_build


class TestBuild(unittest.TestCase):
    def test_build_minimal(self):
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
            rep = run_build(cwd=root, skip_import=False)
            self.assertTrue(any(s.name == "app/main.py" and s.ok for s in rep.steps))
            self.assertTrue(any(s.name == "x_element.js" and s.ok for s in rep.steps))
            imp = next(s for s in rep.steps if s.name.startswith("import"))
            self.assertTrue(imp.ok, imp.detail)
            self.assertTrue(rep.ok, rep.steps)


if __name__ == "__main__":
    unittest.main()
