#!/usr/bin/env python3
"""Per-PR changelog fragments (stdlib only). See changelog.d/README.md.

  python scripts/changelog.py --check            validate changelog.d/ fragments
  python scripts/changelog.py --preview          print the assembled Unreleased section
  python scripts/changelog.py --release X.Y.Z    fold fragments into CHANGELOG.md, delete them
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

# Keep a Changelog section order.
TYPES = ("added", "changed", "deprecated", "removed", "fixed", "security")
NAME = re.compile(r"^[a-z0-9][a-z0-9-]*\.(%s)\.md$" % "|".join(TYPES))
IGNORED = {"README.md", ".gitkeep"}
UNRELEASED = "## Unreleased"
VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def fragments(root: Path) -> list[Path]:
    d = root / "changelog.d"
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir() if p.name not in IGNORED)


def check(root: Path) -> list[str]:
    errors: list[str] = []
    for p in fragments(root):
        rel = f"changelog.d/{p.name}"
        if not p.is_file() or not NAME.match(p.name):
            errors.append(
                f"{rel}: name must be <slug>.<type>.md, slug [a-z0-9-], type one of {', '.join(TYPES)}"
            )
            continue
        lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            errors.append(f"{rel}: empty")
        elif not lines[0].startswith("- ") or any(
            not (ln.startswith("- ") or ln[0].isspace()) for ln in lines
        ):
            errors.append(f"{rel}: every entry must be a '- ' bullet (continuation lines indented)")
    return errors


def _split(text: str) -> tuple[str, str, str]:
    """Return (before heading, Unreleased body, rest from the next ``## `` heading)."""
    lines = text.splitlines(keepends=True)
    try:
        start = next(i for i, ln in enumerate(lines) if ln.rstrip() == UNRELEASED)
    except StopIteration:
        raise SystemExit(f"CHANGELOG.md: no '{UNRELEASED}' heading") from None
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines)
    )
    return "".join(lines[:start]), "".join(lines[start + 1 : end]), "".join(lines[end:])


def assemble(root: Path) -> str:
    """Body of the Unreleased section: existing CHANGELOG.md lines, then typed fragments."""
    _, body, _ = _split((root / "CHANGELOG.md").read_text(encoding="utf-8"))
    parts = [body.strip()] if body.strip() else []
    by_type: dict[str, list[str]] = {t: [] for t in TYPES}
    for p in fragments(root):
        m = NAME.match(p.name)
        if m:
            by_type[m.group(1)].append(p.read_text(encoding="utf-8").strip())
    for t in TYPES:
        if by_type[t]:
            parts.append(f"### {t.capitalize()}\n\n" + "\n".join(by_type[t]))
    return "\n\n".join(parts)


def release(root: Path, version: str) -> None:
    if not VERSION.match(version):
        raise SystemExit(f"--release: expected X.Y.Z, got {version!r}")
    body = assemble(root)
    if not body:
        raise SystemExit("--release: nothing to release (Unreleased and changelog.d/ are empty)")
    path = root / "CHANGELOG.md"
    head, _, rest = _split(path.read_text(encoding="utf-8"))
    today = datetime.date.today().isoformat()
    section = f"{UNRELEASED}\n\n## {version} — {today}\n\n{body}\n\n"
    path.write_text(head + section + rest, encoding="utf-8")
    for p in fragments(root):
        p.unlink()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--preview", action="store_true")
    mode.add_argument("--release", metavar="X.Y.Z")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args(argv)

    errors = check(args.root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.check:
        print(f"changelog.d: {len(fragments(args.root))} fragment(s) OK")
    elif args.preview:
        print(f"{UNRELEASED}\n\n{assemble(args.root)}")
    else:
        release(args.root, args.release)
        print(f"CHANGELOG.md: released {args.release}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
