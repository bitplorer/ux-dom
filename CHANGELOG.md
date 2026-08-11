# Changelog

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

See [MIGRATION_0.1.md](MIGRATION_0.1.md) · [docs/START_HERE.md](docs/START_HERE.md).
