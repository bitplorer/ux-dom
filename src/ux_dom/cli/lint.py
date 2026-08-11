# Copyright (c) 2026 ux-dom
"""``uxdom lint`` — static checks for XElement / route conventions (dev)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class LintIssue:
    path: str
    message: str
    level: str = "warn"  # warn | error


def _find_app_root(start: Optional[Path] = None) -> Optional[Path]:
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / "app").is_dir():
            return p
        if p == p.parent:
            break
    return None


def lint_project(root: Optional[Path] = None) -> list[LintIssue]:
    app_root = root or _find_app_root()
    issues: list[LintIssue] = []
    if app_root is None:
        return [LintIssue(".", "no app/ found", "error")]

    # document loads x_element.js
    doc = app_root / "app" / "document.py"
    if doc.is_file():
        t = doc.read_text(encoding="utf-8")
        if "x_element.js" not in t and "x_element_js" not in t:
            issues.append(
                LintIssue(
                    str(doc.relative_to(app_root)),
                    "document does not load x_element.js — XElement hosts will not upgrade",
                    "warn",
                )
            )
    else:
        issues.append(LintIssue("app/document.py", "missing", "error"))

    # Scan components for XElement subclasses with wrong attrs
    for py in (app_root / "app").rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        try:
            src = py.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = str(py.relative_to(app_root))
        # CustomElement + shadowroot in same render-ish file
        if "CustomElement" in src and re.search(r"shadowroot\s*=", src):
            if "WebComponent" not in src.split("CustomElement")[0][-80:]:
                # heuristic: file uses CustomElement and shadowroot
                if "class " in src and "CustomElement)" in src:
                    issues.append(
                        LintIssue(
                            rel,
                            "CustomElement subclass may set shadowroot — use WebComponent for shadow DOM",
                            "error",
                        )
                    )
        if "WebComponent" in src and "shadowroot" not in src and "shadowdom" not in src:
            if re.search(r"class\s+\w+\(WebComponent\)", src):
                issues.append(
                    LintIssue(
                        rel,
                        "WebComponent subclass should set shadowroot/shadowdom on definition template",
                        "warn",
                    )
                )
        # rejected attr (use x-tagname)
        if "x-component" in src or "x_component=" in src:
            issues.append(
                LintIssue(
                    rel,
                    "x-component is not supported — use x-tagname only",
                    "error",
                )
            )

    # Routes: py files without Component-ish get
    routes = app_root / "app" / "routes"
    if routes.is_dir():
        for py in routes.rglob("*.py"):
            if py.name == "__init__.py":
                continue
            src = py.read_text(encoding="utf-8", errors="ignore")
            if "class " in src and "Component" in src:
                if (
                    "def get" not in src
                    and "routes =" not in src
                    and "routes=" not in src
                ):
                    issues.append(
                        LintIssue(
                            str(py.relative_to(app_root)),
                            "Component route without routes= or get() — DirectoryRouter may skip it",
                            "warn",
                        )
                    )
            elif "class " not in src:
                issues.append(
                    LintIssue(
                        str(py.relative_to(app_root)),
                        "route file has no class — expected a Component",
                        "warn",
                    )
                )

    return issues
