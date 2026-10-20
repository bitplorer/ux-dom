- **Per-PR changelog fragments.** New entries go in `changelog.d/<slug>.<type>.md`
  instead of CHANGELOG.md; `scripts/changelog.py` checks (CI), previews, and folds
  them into CHANGELOG.md on release. See `changelog.d/README.md`.
