# ADR 0004 — No Compatibility Shims Before the First Release

> **Diátaxis:** ADR · **Canonical:** `docs/adr/0004-no-compat-shims-pre-release.md` · **Layer:** ux-dom (repo process)  
> Map: [INDEX.md](../INDEX.md).

**Status:** Accepted  
**Date:** 2026-10-20  
**Scope:** How a PR removes or renames public names, parameters and modules. Applies to
every ux-* repo (ux-dom, ux-channel, ux-behavior, ux-motion, ux-compose) until the first
public release. ux-compose mirrors this ADR.

---

## Context

No ux-* library has been published. The owner (2026-10-20):

> "right now I havent published any ux-* libraries so we can safely weed out any bugs/holes/residuals etc, so instead of deprecating or keeping shims and dead code we can clean up and update"

The audit [#59](https://github.com/bitplorer/ux-dom/issues/59) found shims, aliases and
tombstones kept "for compatibility". Its sibling-repo usage scan shows the only callers
are the other ux-* repos, which we control. There are no external users to protect, so
each shim is dead code that hides the real API and needs its own tests.

## Decision

**Choice:** until the first public release, none of the following is added or kept:

- deprecation periods or `DeprecationWarning` paths;
- compatibility aliases or dual names for one thing;
- re-exports that keep an old import path working;
- tombstones (stub modules or names that only raise or point elsewhere);
- parameters that are accepted but ignored.

Instead:

- **Fix and update every caller in the same train.** A rename or removal lands with the
  matching change in each consumer ux-* repo, merged in lockstep, with the dependency pin
  bumped.
- **Alias-only tests go in the same PR.** A test whose only job is to pin an alias or old
  path is updated or deleted in that PR. This is sanctioned, and the PR body lists each
  such test.
- **Record the break.** Each change is a changelog fragment
  ([ADR 0001](0001-changelog-fragments.md)) of type `removed` or `changed`.

**Exit condition:** this ADR is superseded at the first published release. From then on
a deprecation policy applies, recorded in the ADR that supersedes this one.

**Why:** a shim costs code, tests and docs, and protects nobody before a release.
Removing it now is cheaper than removing it after users depend on it.

## Alternatives

| Option | Verdict | Why |
|--------|---------|-----|
| Keep shims "for compatibility" | Rejected | There are no users; the shims are residue |
| Semver deprecation cycles now | Rejected | Premature: no version has been published to deprecate from |

## Consequences

- PRs may break ux-* consumers, so each break ships with the consumer updates and pin
  bump in the same train.
- Fewer names, paths and tests; `__init__.py` lists only the current API.
- The changelog is the single record of what was removed or renamed.
- At the first release this ADR must be superseded; until then, a reviewer may reject any
  new shim by citing it.
