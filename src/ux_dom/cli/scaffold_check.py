# Copyright (c) 2026 ux-dom
"""Hardened scaffold integrity checks.

Used by:
  * ``create_app`` (post-write validation — fail loud if template broken)
  * ``uxdom doctor`` (project health)
  * tests

Checks are pure filesystem/source inspections (no import of the app) so they
run offline and never pollute ``sys.modules``.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class ScaffoldIssue:
    code: str
    message: str
    level: str = "error"  # error | warn | info
    path: str = ""


@dataclass
class ScaffoldReport:
    root: Path
    issues: list[ScaffoldIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.level == "error" for i in self.issues)

    @property
    def errors(self) -> list[ScaffoldIssue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[ScaffoldIssue]:
        return [i for i in self.issues if i.level == "warn"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "root": str(self.root),
            "issues": [
                {
                    "code": i.code,
                    "level": i.level,
                    "message": i.message,
                    "path": i.path,
                }
                for i in self.issues
            ],
        }


# Core files every create-app tree must have
_REQUIRED_FILES = (
    "app/__init__.py",
    "app/main.py",
    "app/settings.py",
    "app/document.py",
    "app/routes/__init__.py",
    "app/routes/index.py",
    "app/components/layout.py",
    "requirements.txt",
    "README.md",
    ".ux_dom-scaffold.json",
)

_PLACEHOLDER_RE = re.compile(r"\{\{[A-Za-z0-9_]+\}\}")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _has_unresolved_placeholders(text: str) -> list[str]:
    return sorted(set(_PLACEHOLDER_RE.findall(text)))


def _parse_py(path: Path) -> Optional[ast.AST]:
    try:
        return ast.parse(_read(path), filename=str(path))
    except SyntaxError:
        return None


def _meta(root: Path) -> dict[str, Any]:
    meta_path = root / ".ux_dom-scaffold.json"
    if not meta_path.is_file():
        return {}
    try:
        data = json.loads(_read(meta_path))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {"__invalid__": True}


def validate_scaffold(
    root: Path | str,
    *,
    strict: bool = True,
    expect_template: Optional[str] = None,
) -> ScaffoldReport:
    """Validate a create-app project tree.

    ``strict=True`` (default): missing required files / bad syntax / unresolved
    template placeholders are **errors**. Soft mismatches are warnings.
    """
    root = Path(root).resolve()
    report = ScaffoldReport(root=root)

    if not root.is_dir():
        report.issues.append(ScaffoldIssue("root", f"not a directory: {root}", "error"))
        return report

    # ── required files ───────────────────────────────────────────────────
    for rel in _REQUIRED_FILES:
        p = root / rel
        if not p.is_file():
            report.issues.append(
                ScaffoldIssue(
                    "missing_file", f"required file missing: {rel}", "error", rel
                )
            )

    meta = _meta(root)
    if meta.get("__invalid__"):
        report.issues.append(
            ScaffoldIssue(
                "scaffold_meta",
                ".ux_dom-scaffold.json is not valid JSON",
                "error",
                ".ux_dom-scaffold.json",
            )
        )
        meta = {}
    elif not meta:
        report.issues.append(
            ScaffoldIssue(
                "scaffold_meta",
                ".ux_dom-scaffold.json missing or empty",
                "warn" if not strict else "error",
                ".ux_dom-scaffold.json",
            )
        )

    template = str(meta.get("template") or expect_template or "")
    if expect_template and template and template != expect_template:
        report.issues.append(
            ScaffoldIssue(
                "template_mismatch",
                f"meta template={template!r} != expected {expect_template!r}",
                "error",
            )
        )

    # Template-specific routes
    if template == "shop":
        for rel in ("app/routes/shop.py", "app/routes/cart.py"):
            if not (root / rel).is_file():
                report.issues.append(
                    ScaffoldIssue(
                        "template_file", f"shop template needs {rel}", "error", rel
                    )
                )
    elif template == "live":
        for rel in ("app/channel_app.py", "app/routes/live.py"):
            if not (root / rel).is_file():
                report.issues.append(
                    ScaffoldIssue(
                        "template_file", f"live template needs {rel}", "error", rel
                    )
                )
    elif template == "tutorial":
        for rel in (
            "app/routes/htmx_demo.py",
            "app/routes/xelement_demo.py",
            "app/routes/recipes.py",
        ):
            if not (root / rel).is_file():
                report.issues.append(
                    ScaffoldIssue(
                        "template_file", f"tutorial template needs {rel}", "error", rel
                    )
                )

    # Tailwind assets when flag on
    with_tw = meta.get("with_tailwind", True)
    if with_tw:
        for rel in ("assets/css/input.css", "tailwind.config.js", "app/tailwindcss.py"):
            if not (root / rel).is_file():
                report.issues.append(
                    ScaffoldIssue(
                        "tailwind_file",
                        f"with_tailwind but missing {rel}",
                        "error",
                        rel,
                    )
                )

    # ── Python syntax + placeholder leaks ────────────────────────────────
    py_files = list(root.rglob("*.py"))
    # skip venv-ish
    py_files = [
        p for p in py_files if ".venv" not in p.parts and "site-packages" not in p.parts
    ]
    for p in py_files:
        rel = str(p.relative_to(root))
        try:
            text = _read(p)
        except Exception as e:
            report.issues.append(
                ScaffoldIssue("read", f"cannot read {rel}: {e}", "error", rel)
            )
            continue
        ph = _has_unresolved_placeholders(text)
        if ph:
            report.issues.append(
                ScaffoldIssue(
                    "placeholder",
                    f"unresolved template tokens in {rel}: {', '.join(ph)}",
                    "error",
                    rel,
                )
            )
        if _parse_py(p) is None:
            report.issues.append(
                ScaffoldIssue("syntax", f"Python syntax error: {rel}", "error", rel)
            )

    # Non-py text that must not leak placeholders
    for rel in ("README.md", "requirements.txt", ".env.example", "pyproject.toml"):
        p = root / rel
        if not p.is_file():
            continue
        ph = _has_unresolved_placeholders(_read(p))
        if ph:
            report.issues.append(
                ScaffoldIssue(
                    "placeholder",
                    f"unresolved tokens in {rel}: {', '.join(ph)}",
                    "error",
                    rel,
                )
            )

    # ── semantic contracts ───────────────────────────────────────────────
    doc = root / "app" / "document.py"
    if doc.is_file():
        dtxt = _read(doc)
        if "Document(" not in dtxt:
            report.issues.append(
                ScaffoldIssue(
                    "document_shell",
                    "app/document.py must construct Document(...)",
                    "error",
                    "app/document.py",
                )
            )
        if "XElement" not in dtxt and "XElementRuntime" not in dtxt:
            report.issues.append(
                ScaffoldIssue(
                    "document_xelement",
                    "document should .use(XElement()) for x_element.js",
                    "warn",
                    "app/document.py",
                )
            )
        if "def page(" not in dtxt:
            report.issues.append(
                ScaffoldIssue(
                    "document_page",
                    "missing page() helper for stage-B render",
                    "warn",
                    "app/document.py",
                )
            )
        # CSP contract when meta/settings say on
        settings_p = root / "app" / "settings.py"
        stxt = _read(settings_p) if settings_p.is_file() else ""
        csp_on = (
            meta.get("with_csp", True) is not False and "WITH_CSP = False" not in stxt
        )
        if csp_on:
            import re as _re

            has_csp_import = bool(
                _re.search(
                    r"(?:from\s+ux_dom\.runtime\s+import\s+[^\n]*\bCsp\b|from\s+ux_dom\.plugins\.csp\s+import\s+\bCsp\b|import\s+ux_dom\.plugins\.csp)",
                    dtxt,
                )
            )
            has_csp_use = bool(
                _re.search(
                    r"\bCsp\.(?:auto|dev|prod|report_only)\s*\(|\bCsp\s*\(", dtxt
                )
            )
            if not (has_csp_import and has_csp_use):
                report.issues.append(
                    ScaffoldIssue(
                        "document_csp",
                        "WITH_CSP on but document.py must import Csp and call "
                        "Csp.auto()/dev()/prod() (or Csp())",
                        "error",
                        "app/document.py",
                    )
                )
            if "WITH_CSP" not in stxt:
                report.issues.append(
                    ScaffoldIssue(
                        "settings_csp",
                        "settings.py missing WITH_CSP flag",
                        "warn",
                        "app/settings.py",
                    )
                )

    main = root / "app" / "main.py"
    if main.is_file():
        mtxt = _read(main)
        if "FastAPI" not in mtxt:
            report.issues.append(
                ScaffoldIssue(
                    "main_asgi",
                    "app/main.py should construct FastAPI(...)",
                    "error",
                    "app/main.py",
                )
            )
        if "document.mount" not in mtxt and ".mount(" not in mtxt:
            report.issues.append(
                ScaffoldIssue(
                    "main_document_mount",
                    "app/main.py should call document.mount(app)",
                    "error",
                    "app/main.py",
                )
            )
        if "document" not in mtxt:
            report.issues.append(
                ScaffoldIssue(
                    "main_document",
                    "main.py should import/use app.document",
                    "warn",
                    "app/main.py",
                )
            )
        if "directory_routes" not in mtxt and "DirectoryRouter" not in mtxt:
            report.issues.append(
                ScaffoldIssue(
                    "main_routes",
                    "main.py should wire DirectoryRouter / directory_routes",
                    "warn",
                    "app/main.py",
                )
            )

    settings = root / "app" / "settings.py"
    if settings.is_file():
        stxt = _read(settings)
        for flag in ("DEBUG", "WITH_TAILWIND", "WITH_CHANNEL", "WITH_HMR"):
            if flag not in stxt:
                report.issues.append(
                    ScaffoldIssue(
                        "settings_flag",
                        f"settings.py missing {flag}",
                        "warn",
                        "app/settings.py",
                    )
                )
        # meta vs settings consistency
        if meta:
            if meta.get("with_channel") and "WITH_CHANNEL = True" not in stxt:
                report.issues.append(
                    ScaffoldIssue(
                        "meta_channel",
                        "meta with_channel=true but settings.WITH_CHANNEL is not True",
                        "warn",
                    )
                )
            if meta.get("with_tailwind") is False and "WITH_TAILWIND = True" in stxt:
                report.issues.append(
                    ScaffoldIssue(
                        "meta_tailwind",
                        "meta with_tailwind=false but settings.WITH_TAILWIND is True",
                        "warn",
                    )
                )

    # index route must export Index component pattern (soft)
    index = root / "app" / "routes" / "index.py"
    if index.is_file():
        itxt = _read(index)
        if "class Index" not in itxt and "Index" not in itxt:
            report.issues.append(
                ScaffoldIssue(
                    "route_index",
                    "routes/index.py should define Index page",
                    "warn",
                    "app/routes/index.py",
                )
            )
        if "routes" not in itxt:
            report.issues.append(
                ScaffoldIssue(
                    "route_methods",
                    "route module should declare routes = [...]",
                    "warn",
                    "app/routes/index.py",
                )
            )

    # Empty required files
    for rel in _REQUIRED_FILES:
        p = root / rel
        if p.is_file() and p.stat().st_size == 0:
            report.issues.append(
                ScaffoldIssue("empty_file", f"empty required file: {rel}", "error", rel)
            )

    return report


def assert_scaffold_ok(
    root: Path | str, *, expect_template: Optional[str] = None
) -> ScaffoldReport:
    """Raise ``ScaffoldError`` if validation fails (used by create_app)."""
    report = validate_scaffold(root, strict=True, expect_template=expect_template)
    if not report.ok:
        msgs = "; ".join(f"[{i.code}] {i.message}" for i in report.errors[:8])
        raise ScaffoldError(f"scaffold validation failed for {root}: {msgs}")
    return report


class ScaffoldError(RuntimeError):
    """Raised when post-create validation fails."""


def doctor_checks_from_scaffold(root: Path) -> list[dict[str, Any]]:
    """Map scaffold report → doctor-style dicts (name/ok/level/detail)."""
    report = validate_scaffold(root, strict=False)
    out: list[dict[str, Any]] = []
    # summary
    out.append(
        {
            "name": "scaffold:integrity",
            "ok": report.ok,
            "level": "error" if not report.ok else "info",
            "detail": (
                f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)"
                if not report.ok
                else f"ok ({len(report.issues)} soft notes)"
            ),
        }
    )
    for i in report.issues:
        if i.level == "info":
            continue
        out.append(
            {
                "name": f"scaffold:{i.code}",
                "ok": i.level != "error",
                "level": i.level,
                "detail": i.message + (f" ({i.path})" if i.path else ""),
            }
        )
    return out
