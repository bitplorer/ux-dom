# Copyright (c) 2026 ux-dom
"""``uxdom doctor`` — environment and project health checks.

Brand lines: PyPI ``ux-dom`` · import ``ux_dom`` · CLI ``uxdom``.
"""

from __future__ import annotations

import importlib.util
import json
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# CSS compile is product DX: this CLI neither probes nor runs Tailwind, so it
# is a footer note, not a check (reports show only checks that can fail, #73).
CSS_NOTE = "CSS: product CSS is `uxcompose build` (uxdom doctor does not check CSS)"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    level: str = "info"  # info | warn | error


@dataclass
class DoctorReport:
    checks: list[Check] = field(default_factory=list)
    project_root: Optional[Path] = None

    @property
    def ok(self) -> bool:
        return not any(c.level == "error" and not c.ok for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "project_root": str(self.project_root) if self.project_root else None,
            "checks": [
                {
                    "name": c.name,
                    "ok": c.ok,
                    "level": c.level,
                    "detail": c.detail,
                }
                for c in self.checks
            ],
        }


def _find_project(start: Path) -> Optional[Path]:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / ".ux_dom-scaffold.json").exists() or (
            (p / "app" / "main.py").exists() and (p / "app" / "settings.py").exists()
        ):
            return p
        if p == p.parent:
            break
    return None


def run_doctor(*, cwd: Optional[Path] = None) -> DoctorReport:
    """Collect environment + optional project checks."""
    report = DoctorReport()
    cwd = (cwd or Path.cwd()).resolve()

    # Python version
    py = sys.version_info
    py_ok = py >= (3, 14)
    # Version mismatch is a *warn* so local CI / older runners can still
    # build & test; deploy images should still target >= 3.14.
    report.checks.append(
        Check(
            "python",
            py_ok,
            f"{platform.python_version()} ({sys.executable})"
            + ("" if py_ok else " — ux-dom targets Python >= 3.14 (warn)"),
            level="warn" if not py_ok else "info",
        )
    )

    # Core import
    try:
        import ux_dom

        report.checks.append(
            Check("ux_dom", True, f"version {ux_dom.__version__}", "info")
        )
    except Exception as e:
        report.checks.append(Check("ux_dom", False, str(e), "error"))
        return report

    # XElement runtime file
    try:
        from ux_dom.scripts import x_element_js_text

        src = x_element_js_text()
        ok = "x-tagname" in src and "UxDom.XElement" in src
        report.checks.append(
            Check(
                "x_element.js",
                ok,
                (
                    f"{len(src)} bytes in installed package · serve /ux-dom/static/x_element.js"
                    if ok
                    else "runtime missing contract tokens"
                ),
                "error" if not ok else "info",
            )
        )
    except Exception as e:
        report.checks.append(Check("x_element.js", False, str(e), "error"))

    # Optional deps
    for mod, extra in [
        ("fastapi", "fastapi"),
    ]:
        spec = importlib.util.find_spec(mod)
        report.checks.append(
            Check(
                f"dep:{mod}",
                spec is not None,
                "installed" if spec else f"missing — pip install 'ux-dom[{extra}]'",
                "warn" if spec is None else "info",
            )
        )

    # uxchannel soft — report the real import result; a spec alone is not a
    # working install.
    try:
        import ux_channel  # type: ignore

        ch_ok = True
        ch_detail = getattr(ux_channel, "__version__", "installed")
    except Exception as e:
        ch_ok = False
        ch_detail = (
            f"installed but import failed — {type(e).__name__}: {e}"
            if importlib.util.find_spec("ux_channel") is not None
            else "not installed (optional) — pip install 'ux-channel>=0.1.0'"
        )
    report.checks.append(
        Check("ux-channel", ch_ok, str(ch_detail), "info" if ch_ok else "warn")
    )

    # Project
    root = _find_project(cwd)
    report.project_root = root
    if root is None:
        report.checks.append(
            Check(
                "project",
                True,
                f"no ux-dom app detected under {cwd} (ok if global check)",
                "info",
            )
        )
    else:
        report.checks.append(Check("project", True, str(root), "info"))
        meta = root / ".ux_dom-scaffold.json"
        if meta.exists():
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                report.checks.append(
                    Check(
                        "scaffold",
                        True,
                        f"template={data.get('template')} channel={data.get('with_channel')}",
                        "info",
                    )
                )
            except Exception as e:
                report.checks.append(Check("scaffold", False, str(e), "warn"))

        main = root / "app" / "main.py"
        doc = root / "app" / "document.py"
        dtxt = doc.read_text(encoding="utf-8") if doc.is_file() else ""
        report.checks.append(
            Check(
                "app/main.py",
                main.is_file(),
                str(main),
                "error" if not main.is_file() else "info",
            )
        )
        report.checks.append(
            Check(
                "app/document.py",
                doc.is_file(),
                str(doc) if doc.is_file() else "missing document shell",
                "error" if not doc.is_file() else "info",
            )
        )
        if main.is_file():
            mtxt = main.read_text(encoding="utf-8")
            has_rt = (
                "XElementRuntime" in mtxt
                or "XElement(" in mtxt
                or "xelement=True" in mtxt
                or "document.mount" in mtxt
            )
            # document.py may own runtimes
            has_rt = has_rt or "XElement(" in dtxt or "XElementRuntime" in dtxt
            report.checks.append(
                Check(
                    "main:XElementRuntime",
                    has_rt,
                    (
                        "XElement via Document.use + document.mount"
                        if has_rt
                        else "document.use(XElement()) for x_element.js"
                    ),
                    "warn" if not has_rt else "info",
                )
            )
        if doc.is_file():
            has_shell = (
                "Document(" in dtxt or ".use(" in dtxt or "include_runtimes" in dtxt
            )
            report.checks.append(
                Check(
                    "document:shell",
                    has_shell,
                    (
                        "Document shell present (Document + .use)"
                        if has_shell
                        else "prefer Document(...).use(XElement(), Htmx())"
                    ),
                    "warn" if not has_shell else "info",
                )
            )
        # Product scaffold is uxcompose. Leftover .ux_dom-scaffold.json is info only.
        report.checks.append(
            Check(
                "product-scaffold",
                True,
                "product apps: uxcompose create-app (uxdom does not scaffold)",
                "info",
            )
        )

        # Optional dual-copy file is NOT required
        xjs = root / "assets" / "js" / "x_element.js"
        if xjs.is_file():
            report.checks.append(
                Check(
                    "assets/js/x_element.js",
                    True,
                    "present (app dual-copy; package mount is preferred)",
                    "info",
                )
            )

    return report


def format_report(report: DoctorReport) -> str:
    lines = [
        "uxdom doctor",
        "=" * 40,
        "Brand lines",
        "  PyPI / pip : ux-dom",
        "  import     : ux_dom",
        "  CLI        : uxdom",
        "-" * 40,
    ]
    if report.project_root:
        lines.append(f"project: {report.project_root}")
    for c in report.checks:
        mark = "OK " if c.ok else ("!! " if c.level == "error" else "?? ")
        lines.append(f"  [{mark.strip():2}] {c.name}: {c.detail}")
    lines.append("=" * 40)
    lines.append("PASS" if report.ok else "FAIL (see errors above)")
    lines.append(CSS_NOTE)
    return "\n".join(lines)
