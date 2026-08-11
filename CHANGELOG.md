# Changelog

## Unreleased

### Docs / maintainership

- **Automation-first policy:** ceremonial app files default to `uxdom create-app` /
  `uxdom add`; hand-code only when extending features or making breaking changes
  ([DX.md](docs/guides/DX.md), [MAINTENANCE_CANON.md](docs/ship/MAINTENANCE_CANON.md) §5.5,
  [AGENTS.md](AGENTS.md)).
- **Freshness pass:** fixed nested doc links (guides/internals/security/ship),
  full test package paths (`tests/0N_*`), removed dead `MIGRATION_0.1` / `BUGS_AUDIT`
  references, restored [docs/archive/](docs/archive/) index, corrected package-mount
  XElement URL in [STABILITY.md](docs/ship/STABILITY.md).
- **Architecture overviews** at composition, routing, module map, design canon,
  APP_COMPOSITION / DOCUMENT_AND_APP (no longer empty “superseded” stubs).

## 0.1.0 — ux-dom (first public line)

**Brand:** dist `ux-dom` · import `ux_dom` · CLI **`uxdom`** (unhyphenated).

Companion control plane: dist `ux-channel` · import `ux_channel` · CLI **`uxchannel`**.

| Surface | Value |
|---------|--------|
| Version | **0.1.0** |
| Document runtime | `.use` / `.mount`, XElement, Htmx, Csp, Channel |
| Control attrs | `.as_ux_dom()` (from ux-channel) |
| Static | `/ux-dom/static/x_element.js` (single-copy) |
| Wire (channel) | `data-channel-*`, `X-Channel-*` |

No shims for historical names (`uidom`, `ui_dom`, `ui-dom`).

### Architecture
- **Document** is the HTML shell source of truth
- Scaffold: FastAPI + `document.mount` + DirectoryRouting
- Concurrent tree locks; fail-closed reactive re-render

### Features
- `uxdom create-app` / `dev` / `doctor` / `add` / `build` / `deploy`
- XElement + `x_element.js`, DirectoryRouter `[id]` segments
- Nonce CSP, SafeStatic, streaming HTML, sync/async render
- ReactiveComponent (dataclass state + snapshot/rollback)

### Quality
- Ontological tests (`tests/01_core` … `06_browser`)
- Chaos / load / pentest batteries; browser harnesses

See [docs/START_HERE.md](docs/START_HERE.md) · [docs/ship/STABILITY.md](docs/ship/STABILITY.md).
