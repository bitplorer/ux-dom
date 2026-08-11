# Stability & brittle edges (0.1)

This document records **edges that bit us**, what we hardened, and how to stay robust.
It is also the live stand-in for a separate bugs audit (see [archive/](../archive/)).

## Hardened in this cut

| Edge | Failure mode | Fix |
|------|--------------|-----|
| `route.py` + Component | `uxdom add route users/[id]` wrote Component; DirectoryRouter only registered bare `get()` functions → **404** | DirectoryRouter discovers **Components with `routes=` inside `route.py`**; URL is `/{Class}` not `/route/{Class}` |
| `get(cls, **path_params)` | FastAPI treats `path_params` as required **query** → **422** | Generated `get(cls, id: str)` named params |
| Nested packages | Missing `users/__init__.py` | `_ensure_route_packages` writes all `__init__.py` |
| `shadowdom=True` | Emitted `shadowdom="shadowdom"` | Use `shadowroot="true"` / string modes |
| `uxdom build` css step | Soft step could flip ok incorrectly | Informational only; Tailwind step is authoritative |
| Dockerfile CMD | Hard-coded port ignored host `PORT` | `uvicorn … --port ${PORT:-8080}` |
| `uxdom dev` imports | `app` not on path | Prepend cwd to `PYTHONPATH` / `sys.path` |
| Dual JS names | Cognitive load | Single `x_element.js` / `x-tagname` |

## Still intentionally soft

| Item | Why |
|------|-----|
| uxchannel tests skipped without package | Optional companion |
| Tailwind in Docker | Best-effort; CDN apps skip CLI |
| `uxdom deploy` no cloud upload | No secrets in CLI; host CLI publishes |
| Advanced `WebComponentSlot` | Prefer plain WebComponent + `slot()` |

## Stability gates

```bash
python -m pytest tests/ -q
python -m pytest tests/03_routing_cli/test_cli_route_maturity.py \
  tests/03_routing_cli/test_dx_cli.py tests/03_routing_cli/test_build_deploy.py -q
node tests/browser/x_element_harness.mjs
python -m pytest tests/06_browser/test_kit_browser_deep.py -q   # needs playwright + network for CDNs
uxdom doctor
```

## Authoring rules (keep sturdy)

1. **XElement:** only `x-tagname`; light vs shadow base classes matter.
2. **Routes:** Components need `routes = ["get"]` + `get` classmethod; path params by name.
3. **`route.py`:** means “this folder’s index module” — class name appears in URL (`/users/{id}/Page`).
4. **Never** boolean HTML attrs that stringify to the attribute name for multi-value attrs (`shadowdom=True`).
5. **Document** serves library JS from the **package mount** by default:
   `/ux-dom/static/x_element.js` (not dual-copy under `/assets/js/` unless
   `serve="webassets"` escape hatch).
6. **Ceremonial files:** generate via `uxdom create-app` / `uxdom add` — hand-edit
   only when extending features or changing contracts.

## DX command surface (stable)

`create-app` · `dev` · `doctor` · `build` · `deploy` · `add` · `lint` ·
`templates` · `examples` · `plugins` · `profile` · `dashboard`

## UI kit stability (0.1+)

| Edge | Hardening |
|------|-----------|
| Tabs Alpine keys | Non-identifier keys → `tabN` (no JS break/XSS via quotes) |
| Tabs item shape | `ValueError` if not `(key,label,body)` |
| Select selected | Only emit `selected` when true; value= honors option |
| Dialog attrs | Preserve Alpine `x-data` unless caller overrides |
| Dialog None parts | No `None` children |
| Button disabled=False | Attribute omitted |
| `uxdom add ui Dialog` | Auto-copies `button` + `tokens` dependency |
| Copy imports | Regex rewrite `ux_dom.ui.*` → relative |
| Channel bridge | Soft-import; stub attrs without uxchannel |

Gates: `tests/02_document_plugins/test_ui_kit.py` ·
`tests/04_production/test_production_stability.py` ·
`tests/03_routing_cli/test_cli_route_maturity.py`
