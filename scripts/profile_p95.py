#!/usr/bin/env python3
"""Maintainer alias → first-class DX: ``uxdom profile``."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ux_dom.cli.profile import format_profile_report, run_profile

def main(argv=None):
    out = ROOT / "reports" / "p95"
    report = run_profile(out=out)
    print(format_profile_report(report))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
