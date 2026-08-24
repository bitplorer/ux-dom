# Design canon (ux-dom)

## Non-negotiable

1. **Render only** — trees → dunders → HTML/stream. Product delivery is ux-compose.
2. **Document.use** owns shell meaning (control, runtime tags, CSP stamp, style).
3. **Single product path** — `uxcompose create-app | build | serve | deploy` only.
4. **Pure discovery** — `DirectoryRoutes` + `RouterHooks` are host-free.
5. **No dual App** — do not recommend `plugins.App.web` as product entry.

## CLI side-effect policy (pure-dom)

| Command | Writes? | Notes |
|---------|---------|--------|
| `doctor` / `lint` / `info` | No | Read-only |
| `build` | leftover Document/static verify (`app/main.py`); no CLI download | flags |
| `add` | Yes | refuse existing unless `--force` |
| `profile` / `dashboard` | reports/ only | |

Product create-app / build / serve / deploy: **uxcompose** (not this package).

## Greenfield

| Need | Command |
|------|---------|
| Product app | `uxcompose create-app` |
| Pure-dom stubs | `uxdom add component\|xelement\|ui` |

## See also

[SYSTEM.md](SYSTEM.md) · ux-compose `docs/FLOW.md`
