"""Hardening: docs links + source doc pointers stay live (no stale flat paths)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
SRC = ROOT / "src" / "ux_dom"

# Flat basenames that must never appear as docs/<NAME>.md once nested
NESTED_BASENAMES = {
    "XELEMENT.md",
    "DOCUMENT.md",
    "CSP.md",
    "SAFE_STATIC.md",
    "ASSETS.md",
    "UI.md",
    "TUTORIAL.md",
    "COOKBOOK.md",
    "HYPERMEDIA.md",
    "PRODUCTION_READINESS.md",
    "CLI.md",
    "DX.md",
    "ROUTING.md",
    "COMPONENTS.md",
    "REACTIVE.md",
    "ARCHITECTURE.md",
    "RENDER_PHASES.md",
    "MEMBERSHIP.md",
    "CONCURRENCY.md",
    "DEPLOY.md",
    "MAINTENANCE_CANON.md",
}

DEAD_DOCS = {
    "docs/CONSISTENCY_REPORT.md",
    "docs/BUGS_AUDIT.md",
    "MIGRATION_0.1.md",
    "QUICKSTART.md",
}


def _markdown_files() -> list[Path]:
    out: list[Path] = []
    for base in (ROOT,):
        for p in base.rglob("*.md"):
            if ".git" in p.parts or ".venv" in p.parts or "node_modules" in p.parts:
                continue
            out.append(p)
    return out


class TestMarkdownLinksResolve(unittest.TestCase):
    def test_relative_markdown_links_exist(self):
        link_re = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
        broken: list[str] = []
        for path in _markdown_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            for m in link_re.finditer(text):
                url = m.group(2).strip()
                if url.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                url_path = url.split("#")[0].split("?")[0]
                if not url_path:
                    continue
                target = (path.parent / url_path).resolve()
                try:
                    target.relative_to(ROOT.resolve())
                except ValueError:
                    continue
                if not target.exists():
                    broken.append(f"{path.relative_to(ROOT)} -> {url}")
        self.assertEqual(broken, [], "broken markdown links:\n" + "\n".join(broken[:40]))


class TestNoStaleFlatDocPaths(unittest.TestCase):
    def test_source_and_docs_avoid_flat_nested_names(self):
        """``docs/XELEMENT.md`` etc. must point at nested paths that exist."""
        bad: list[str] = []
        # paths like docs/FOO.md where FOO is a nested guide basename
        pat = re.compile(r"(?<![\w./-])docs/([A-Z][A-Z0-9_]+\.md)\b")
        scan_roots = [SRC, DOCS, ROOT / "examples", ROOT / "standalone", ROOT / "scripts"]
        for root in scan_roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {
                    ".py",
                    ".md",
                    ".mjs",
                    ".js",
                    ".sh",
                    ".txt",
                }:
                    continue
                if "__pycache__" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                for m in pat.finditer(text):
                    name = m.group(1)
                    flat = f"docs/{name}"
                    ctx = text[max(0, m.start() - 100) : m.end() + 100]
                    anti = any(
                        k in ctx.lower()
                        for k in (
                            "flat",
                            "do not invent",
                            "stale",
                            "anti-pattern",
                            "must not",
                            "placeholder",
                        )
                    )
                    # placeholder examples like docs/FOO.md
                    if name in {"FOO.md", "BAR.md", "NAME.md"}:
                        continue
                    if name not in NESTED_BASENAMES:
                        # top-level docs like START_HERE.md, FEATURES.md are valid
                        if (DOCS / name).is_file():
                            continue
                        if anti:
                            continue
                        bad.append(f"{path.relative_to(ROOT)}: unknown {flat}")
                        continue
                    # nested basenames must not use flat docs/NAME.md
                    if anti:
                        continue
                    bad.append(f"{path.relative_to(ROOT)}: stale flat path {flat}")
                for dead in DEAD_DOCS:
                    if dead not in text:
                        continue
                    # allow every occurrence that is clearly historical/meta
                    start = 0
                    while True:
                        ctx_i = text.find(dead, start)
                        if ctx_i < 0:
                            break
                        ctx = text[max(0, ctx_i - 80) : ctx_i + len(dead) + 80]
                        start = ctx_i + len(dead)
                        if any(
                            k in ctx.lower()
                            for k in (
                                "no separate",
                                "removed",
                                "dead",
                                "historical",
                                "archive",
                                "not product",
                            )
                        ):
                            continue
                        bad.append(f"{path.relative_to(ROOT)}: dead ref {dead}")
        self.assertEqual(bad, [], "stale/dead doc paths:\n" + "\n".join(bad[:50]))


class TestSingleCopyMessaging(unittest.TestCase):
    def test_cli_build_help_not_dual_copy(self):
        cli = (SRC / "cli" / "cli.py").read_text(encoding="utf-8")
        self.assertNotIn(
            "copied from the installed ux_dom package into\n    assets/js/",
            cli,
        )
        self.assertIn("/ux-dom/static/x_element.js", cli)

    def test_deploy_doc_single_copy(self):
        deploy = (DOCS / "ship" / "DEPLOY.md").read_text(encoding="utf-8")
        self.assertIn("/ux-dom/static/x_element.js", deploy)
        self.assertNotIn(
            "copied from the\ninstalled `ux_dom` package into `assets/js/`",
            deploy,
        )


class TestXElementPackageUrlContract(unittest.TestCase):
    def test_runtime_url_constant(self):
        from ux_dom.plugins.runtime import XELEMENT_JS_URL, XElementRuntime

        self.assertEqual(XELEMENT_JS_URL, "/ux-dom/static/x_element.js")
        rt = XElementRuntime()
        files = list(rt.served_files())
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].url, XELEMENT_JS_URL)


if __name__ == "__main__":
    unittest.main()
