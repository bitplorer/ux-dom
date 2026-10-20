- **Docs: ADR 0004 drops compatibility shims before the first release.** Until a ux-*
  library is published, no deprecation periods, aliases, old-path re-exports, tombstones,
  ignored parameters or dual names; callers in every ux-* repo are updated in the same
  train and breaks are recorded as ``removed`` / ``changed`` fragments.
