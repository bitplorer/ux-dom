# Copyright (c) 2026 ux-dom
"""``uxdom build`` — Document/static verify.

Single-copy model
-----------------
1. XElement JS lives only in the installed ux_dom package.
2. Browser URL: ``/ux-dom/static/x_element.js`` (mounted from site-packages).
3. Build verifies the package file; does not dual-copy into app assets/.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class BuildStep:
    name: str
    ok: bool
    detail: str


@dataclass
class BuildReport:
    root: Path
    steps: list[BuildStep] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "root": str(self.root),
            "steps": [
                {"name": s.name, "ok": s.ok, "detail": s.detail} for s in self.steps
            ],
        }


def _find_app_root(start: Optional[Path] = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / "app" / "main.py").is_file():
            return p
        if p == p.parent:
            break
    raise FileNotFoundError(
        "no pure-dom app found (expected app/main.py). "
        "Product apps from uxcompose create-app have app.py — use: uxcompose build. "
        "This pipeline is Document/static verify for showcase trees."
    )


def run_build(
    *,
    cwd: Optional[Path] = None,
    skip_import: bool = False,
    skip_static_sync: bool = False,
) -> BuildReport:
    """
    Document/static verify pipeline (not product CSS compile):

    1. Structure checks
    2. Sync static runtimes (x_element.js) from installed ux_dom
    3. Import ``app.main:app``
    4. Soft doctor

    This pipeline never compiles or minifies CSS; product CSS is
    ``uxcompose build``. There are deliberately no ``minify`` /
    ``skip_tailwind`` parameters: passing them is a ``TypeError``.
    """
    root = _find_app_root(cwd)
    report = BuildReport(root=root)

    main = root / "app" / "main.py"
    report.steps.append(
        BuildStep(
            "app/main.py",
            main.is_file(),
            str(main) if main.is_file() else "missing",
        )
    )

    # ── static JS sync (package data → project assets/) ──────────────────
    if skip_static_sync:
        report.steps.append(BuildStep("static-sync", True, "skipped"))
    else:
        try:
            from ux_dom.cli.static_assets import sync_runtime_assets

            sync = sync_runtime_assets(root)
            mount_bits = [f"{p}→{d}" for p, d in sync.mounts]
            file_bits = [f"{f.rel} ({f.action}, {f.bytes}B)" for f in sync.files]
            detail = "; ".join(sync.errors + mount_bits + file_bits)
            report.steps.append(
                BuildStep("static-sync", sync.ok, detail or "no mounts or files")
            )
        except Exception as e:
            report.steps.append(BuildStep("static-sync", False, str(e)))

    # Single-copy model: x_element.js lives in installed ux_dom package
    try:
        from ux_dom.scripts import x_element_js_text
        from ux_dom.plugins.runtime import XELEMENT_JS_URL

        src = x_element_js_text()
        report.steps.append(
            BuildStep(
                "x_element.js",
                bool(src) and len(src) > 100,
                f"installed package → serve {XELEMENT_JS_URL} (no app copy required)",
            )
        )
    except Exception as e:
        report.steps.append(BuildStep("x_element.js", False, str(e)))

    # ── Import ASGI app ──────────────────────────────────────────────────
    if skip_import:
        report.steps.append(BuildStep("import", True, "skipped"))
    else:
        env = os.environ.copy()
        path_bits = [str(root)]
        try:
            import ux_dom as _ux

            path_bits.append(str(Path(_ux.__file__).resolve().parents[1]))
        except Exception:
            pass
        if env.get("PYTHONPATH"):
            path_bits.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(path_bits)
        code = (
            "import importlib; "
            "m = importlib.import_module('app.main'); "
            "assert hasattr(m, 'app'), 'app.main:app missing'; "
            "print(type(m.app).__name__)"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
        detail = (proc.stdout or proc.stderr or "").strip()[:2000]
        report.steps.append(
            BuildStep(
                "import:app.main:app",
                proc.returncode == 0,
                detail or f"exit {proc.returncode}",
            )
        )

    # ── doctor soft ──────────────────────────────────────────────────────
    try:
        from ux_dom.cli.doctor import run_doctor

        doc = run_doctor(cwd=root)
        hard = [c for c in doc.checks if c.level == "error" and not c.ok]
        report.steps.append(
            BuildStep(
                "doctor",
                len(hard) == 0,
                f"{sum(1 for c in doc.checks if c.ok)}/{len(doc.checks)} checks ok"
                + (f" · hard fails: {[c.name for c in hard]}" if hard else ""),
            )
        )
    except Exception as e:
        report.steps.append(BuildStep("doctor", False, str(e)))

    return report


def format_build_report(report: BuildReport) -> str:
    lines = ["ux-dom build", f"root: {report.root}", "=" * 48]
    for s in report.steps:
        mark = "OK" if s.ok else "FAIL"
        lines.append(f"  [{mark:4}] {s.name}: {s.detail}")
    lines.append("=" * 48)
    lines.append("BUILD OK" if report.ok else "BUILD FAILED")
    return "\n".join(lines)
