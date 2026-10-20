# ADR 0001 — Per-PR Changelog Fragments

> **Diátaxis:** ADR · **Canonical:** `docs/adr/0001-changelog-fragments.md` · **Layer:** ux-dom (repo process)  
> Map: [INDEX.md](../INDEX.md).

**Status:** Accepted  
**Date:** 2026-10-20  
**Scope:** How a PR records its CHANGELOG entry. Applies to every PR into `main`.

---

## Context

Every PR appended a bullet to the top of `## Unreleased` in `CHANGELOG.md`.
Sequential merges therefore all edit the same few lines, and each merge left the
next open PR in conflict. Evidence:

- Merge commit `35ca9d6` ("Merge branch 'main' into chore/remove-deprecations")
  carries a hand-resolved `CHANGELOG.md` conflict (`git show --cc 35ca9d6 -- CHANGELOG.md`).
- The audit issue [#59](https://github.com/bitplorer/ux-dom/issues/59), section
  "Lessons recorded", logs that every PR appends to Unreleased, so sequential
  merges conflict every time.

## Decision

**Choice:** Each PR adds one fragment file, `changelog.d/<slug>.<type>.md`, and does
not edit `CHANGELOG.md`. `<type>` is a Keep a Changelog section (`added`, `changed`,
`deprecated`, `removed`, `fixed`, `security`). `scripts/changelog.py` (stdlib only):

- `--check` validates names, types and non-empty bullet content; it runs in the CI
  `quality` job.
- `--preview` prints the assembled Unreleased section.
- `--release X.Y.Z` folds fragments into `CHANGELOG.md` under `## X.Y.Z — <date>`
  and deletes them.

Entries already under `## Unreleased` stay where they are; `--release` keeps them
first, then appends one `### <Type>` subsection per fragment type.

**Why:** distinct files never conflict, so PRs merge in any order without a rebase.
The convention is enforced by one small script with no new dependency.

## Alternatives

| Option | Verdict | Why |
|--------|---------|-----|
| Keep editing `CHANGELOG.md` | Rejected | The conflict this ADR removes |
| `merge=union` driver in `.gitattributes` | Rejected | Only applies to local merges, not GitHub's merge button or rebase in the web UI; silently interleaves or duplicates lines |
| [towncrier](https://towncrier.readthedocs.io/) | Rejected | Same model, but an extra dependency and config for a ~100-line job |

## Consequences

- Contributors write a fragment instead of a CHANGELOG line
  ([CONTRIBUTING.md](../../CONTRIBUTING.md#changelog), [changelog.d/README.md](../../changelog.d/README.md)).
- `CHANGELOG.md` shows released history plus pre-convention Unreleased lines; the
  pending entries are visible with `--preview`.
- Release is one command; the maintainer reviews the diff before tagging.
