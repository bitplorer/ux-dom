# changelog.d — per-PR changelog fragments

Each PR adds **one file** here instead of editing [CHANGELOG.md](../CHANGELOG.md).
Two PRs never touch the same line, so they never conflict. Why:
[ADR 0001](../docs/adr/0001-changelog-fragments.md).

## Name

`<slug>.<type>.md`

- `<slug>`: the PR number or branch slug, `[a-z0-9-]` (e.g. `71`, `fix-csp-presets`).
- `<type>`: one of `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`
  ([Keep a Changelog](https://keepachangelog.com/en/1.1.0/) sections).

## Content

One or a few Markdown bullets in the CHANGELOG.md style. Continuation lines are indented.

```markdown
- **Fix: ``Csp`` presets honour later field edits.** ``c.debug_header = True``
  now reaches ``to_policy()``.
```

## Commands

```bash
python scripts/changelog.py --check          # CI: names, types, non-empty bullets
python scripts/changelog.py --preview        # print the assembled Unreleased section
python scripts/changelog.py --release X.Y.Z  # fold into CHANGELOG.md, delete fragments
```

`--release` keeps the lines already under `## Unreleased` in CHANGELOG.md first,
then adds one `### <Type>` subsection per fragment type, under `## X.Y.Z — <today>`.
