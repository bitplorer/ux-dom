# Changelog

## Unreleased

### Hardening

- **Tailwind scaffold without CLI:** `TailwindCommand` still writes v4 input CSS when
  `tailwindcss` is not on PATH (create-app / doctor layouts stay complete).
- **Single-copy messaging:** CLI `uxdom build` help + `docs/ship/DEPLOY.md` match
  package-mount `/ux-dom/static/x_element.js` (no dual-copy default).
- **Doc path integrity:** source/docs pointers use nested paths
  (`docs/guides/…`, `docs/security/…`, `docs/ship/…`); dead refs removed.
- **Gates:** `tests/04_production/test_docs_integrity.py` (markdown links, flat-path
  ban, single-copy messaging, XElement URL). `scripts/quality.sh` targets `src/ux_dom`.

### Docs / maintainership

- **Automation-first policy:** ceremonial app files default to `uxdom create-app` /
  `uxdom add`; hand-code only when extending features or making breaking changes
  ([DX.md](docs/guides/DX.md), [MAINTENANCE_CANON.md](docs/ship/MAINTENANCE_CANON.md) §5.5,
  [AGENTS.md](AGENTS.md)).
- **Freshness pass:** fixed nested doc links, full test package paths, archive index,
  package-mount XElement URL in [STABILITY.md](docs/ship/STABILITY.md).
- **Architecture overviews** at composition, routing, module map, design canon.

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
