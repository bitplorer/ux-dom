# Copyright (c) 2026 ux-dom
"""``uxdom build`` — production checks + optional runnable package.

Single-copy model
-----------------
1. XElement JS lives only in the installed ux_dom package.
2. Browser URL: ``/ux-dom/static/x_element.js`` (mounted from site-packages).
3. Build verifies the package file; does not dual-copy into app assets/.
4. ``--package`` ships app code + requirements; pip provides library JS at runtime.
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
    package_path: Optional[Path] = None

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "root": str(self.root),
            "package_path": str(self.package_path) if self.package_path else None,
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
        "no ux-dom app found (expected app/main.py). "
        "Run from a create-app project root."
    )


def run_build(
    *,
    cwd: Optional[Path] = None,
    skip_tailwind: bool = False,
    skip_import: bool = False,
    skip_static_sync: bool = False,
    package: bool = False,
    archive: bool = False,
    out_dir: Optional[Path] = None,
    package_name: Optional[str] = None,
    minify: bool = True,
) -> BuildReport:
    """
    Production build pipeline:

    1. Structure checks
    2. Sync static runtimes (x_element.js) from installed ux_dom
    3. Tailwind (if present)
    4. Import ``app.main:app``
    5. Soft doctor
    6. Optional: materialize ``dist/<name>/`` runnable package
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

            sync = sync_runtime_assets(root, force=True)
            # Single-copy model: package mounts are success even with zero app files
            mount_bits = [f"{p}→{d}" for p, d in getattr(sync, "mounts", [])]
            file_bits = [f"{f.rel} ({f.action}, {f.bytes}B)" for f in sync.files]
            detail = "; ".join(mount_bits + file_bits) or "no mounts or files"
            ok = bool(sync.mounts) or bool(sync.files) or sync.ok
            report.steps.append(BuildStep("static-sync", ok, detail))
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

    # Ensure create-app style StaticFiles mount hint (informational)
    main_txt = main.read_text(encoding="utf-8") if main.is_file() else ""
    mounts_assets = "/assets" in main_txt or "StaticFiles" in main_txt
    report.steps.append(
        BuildStep(
            "assets-mount",
            True,  # soft — custom hosts may mount differently
            (
                "app.main references StaticFiles or /assets"
                if mounts_assets
                else "WARNING: app.main may not mount assets/ — ensure /assets/js/* is served"
            ),
        )
    )

    # ── Tailwind (standalone CLI first; app.tailwindcss fallback) ─────────
    tw_mod = root / "app" / "tailwindcss.py"
    if skip_tailwind:
        report.steps.append(BuildStep("tailwind", True, "skipped"))
    else:
        compiled = False
        try:
            from ux_dom.cli.tailwind import (
                argv_with_io,
                discover_css_io,
                resolve_tailwind,
            )

            io = discover_css_io(root)
            hit = resolve_tailwind(cwd=root, ensure=True) if io else None
            if io and hit:
                input_css, output_css = io
                cmd = argv_with_io(
                    hit.argv,
                    input_css=input_css,
                    output_css=output_css,
                    minify=minify,
                    watch=False,
                )
                env = os.environ.copy()
                env["PYTHONPATH"] = os.pathsep.join(
                    [str(root), env.get("PYTHONPATH", "")]
                )
                proc = subprocess.run(
                    cmd,
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    timeout=180,
                    env=env,
                )
                out = (proc.stdout or "") + (proc.stderr or "")
                report.steps.append(
                    BuildStep(
                        "tailwind",
                        proc.returncode == 0,
                        f"{hit.source} exit {proc.returncode}"
                        + (f" · {out.strip()[:200]}" if out.strip() else ""),
                    )
                )
                compiled = True
        except Exception as e:
            report.steps.append(BuildStep("tailwind", False, f"standalone: {e}"))
            compiled = True  # don't also run the python -m fallback after a hard fail

        if not compiled and tw_mod.is_file():
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join([str(root), env.get("PYTHONPATH", "")])
            proc = subprocess.run(
                [sys.executable, "-m", "app.tailwindcss"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=180,
                env=env,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            report.steps.append(
                BuildStep(
                    "tailwind",
                    proc.returncode == 0,
                    f"exit {proc.returncode}"
                    + (f" · {out.strip()[:200]}" if out.strip() else ""),
                )
            )
        elif not compiled:
            report.steps.append(
                BuildStep(
                    "tailwind", True, "no assets/css/input.css (CDN or external CSS)"
                )
            )

        css_candidates = (
            list((root / "assets" / "css").glob("*.css"))
            if (root / "assets" / "css").is_dir()
            else []
        )
        out_css = root / "assets" / "static" / "file" / "css" / "output.css"
        if out_css.is_file():
            css_candidates.append(out_css)
        report.steps.append(
            BuildStep(
                "css-artifacts",
                True,
                ", ".join(str(p.relative_to(root)) for p in css_candidates[:5])
                or "no css files yet under assets/css",
            )
        )

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

        doc = run_doctor(cwd=root, prod=True)
        hard = [
            c
            for c in doc.checks
            if c.level == "error" and not c.ok and c.name != "prod:DEBUG"
        ]
        report.steps.append(
            BuildStep(
                "doctor",
                len(hard) == 0,
                f"{sum(1 for c in doc.checks if c.ok)}/{len(doc.checks)} checks ok"
                + (f" · hard fails: {[c.name for c in hard]}" if hard else ""),
            )
        )
        if any(c.name == "prod:DEBUG" and not c.ok for c in doc.checks):
            report.steps.append(
                BuildStep(
                    "prod:DEBUG-note",
                    True,
                    "DEBUG still True in settings — set False before real deploy",
                )
            )
    except Exception as e:
        report.steps.append(BuildStep("doctor", False, str(e)))

    # ── runnable package ─────────────────────────────────────────────────
    if package or archive:
        if not report.ok:
            report.steps.append(
                BuildStep(
                    "package",
                    False,
                    "skipped — earlier build steps failed",
                )
            )
        else:
            try:
                from ux_dom.cli.static_assets import write_runnable_package

                path = write_runnable_package(
                    root,
                    out_dir=out_dir or (root / "dist"),
                    name=package_name,
                    archive=archive,
                )
                report.package_path = path
                # verify package contains x_element.js
                if path.is_dir():
                    ok = (
                        (path / "run.sh").is_file()
                        and (path / "MANIFEST.json").is_file()
                        and (path / "app" / "main.py").is_file()
                    )
                    report.steps.append(
                        BuildStep(
                            "package",
                            ok,
                            f"{path} (run.sh + MANIFEST; JS from site-packages)",
                        )
                    )
                else:
                    # tar.gz
                    report.steps.append(
                        BuildStep("package", path.is_file(), f"archive {path}")
                    )
            except Exception as e:
                report.steps.append(BuildStep("package", False, str(e)))

    return report


def format_build_report(report: BuildReport) -> str:
    lines = ["ux-dom build", f"root: {report.root}", "=" * 48]
    for s in report.steps:
        mark = "OK" if s.ok else "FAIL"
        lines.append(f"  [{mark:4}] {s.name}: {s.detail}")
    if report.package_path:
        lines.append(f"  package → {report.package_path}")
    lines.append("=" * 48)
    lines.append("BUILD OK" if report.ok else "BUILD FAILED")
    if report.ok and report.package_path:
        lines.append(
            f"Run: cd {report.package_path} && ./run.sh"
            if report.package_path.is_dir()
            else f"Extract {report.package_path} then ./run.sh"
        )
    return "\n".join(lines)
