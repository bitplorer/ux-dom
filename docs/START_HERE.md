# Start here — ux-dom 0.1.0

> Full feature encyclopedia: **[FEATURES.md](FEATURES.md)**.  
> Design & architecture: **[internals/ARCHITECTURE.md](internals/ARCHITECTURE.md)** ·
> **[internals/DESIGN_CANON.md](internals/DESIGN_CANON.md)**.


### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** |

## Mental model (memorize this)

```text
Document  →  HTML shell (<head>/<body>) + .use(runtimes) + .mount(app)
FastAPI   →  process, routes, servers
CLI       →  create-app / add for ceremonial files (default)
```

| Owns | Does **not** own |
|------|------------------|
| **Document** — tag placement, runtime scripts, middleware attach | ASGI process |
| **FastAPI** — routes, lifespan, static mounts | Head/body order |

**Not** the document: `App`, `CreateAsgi` (optional sugar only).

## Day-1

```bash
pip install -e ".[fastapi]"
uxdom create-app myapp
cd myapp
uxdom serve --port 8080
# or: uxdom dev    ·    uxdom start   (prod)
# open /index/Index  ·  /health
```

Prefer **`uxdom create-app` / `uxdom add`** for boilerplate — hand-code only when
extending features or changing contracts ([DX.md](guides/DX.md)).

Scaffold pattern:

```python
# app/document.py
document = Document(...).use(XElement(), Htmx(), Csp.auto())

# app/main.py
app = FastAPI(...)
document.mount(app)
DirectoryRouting(package_dir=PACKAGE, base_directory="routes").include(app)
```

## Core concepts

| Piece | Role |
|-------|------|
| **`Component`** | `render()` → DOM tree; `@dataclass` fields OK |
| **`ReactiveComponent`** | Field mutation re-renders on `str()` / serialize |
| **`with div():` / `async with`** | Build tree (ContextVar-isolated) |
| **`document(*content)`** | Two-stage head/body (page then common) |
| **`DirectoryRouter`** | `routes/users/[id].py` → `/users/{id}` |
| **`XElement`** | Custom element + auto definitions |

## Next reading

1. [INSTALL.md](INSTALL.md)  
2. [TUTORIAL.md](guides/TUTORIAL.md)  
3. [DOCUMENT.md](guides/DOCUMENT.md)  
4. [REACTIVE.md](guides/REACTIVE.md) · [COMPONENTS.md](guides/COMPONENTS.md)  
5. [COOKBOOK.md](guides/COOKBOOK.md) · [ARCHITECTURE.md](internals/ARCHITECTURE.md)  
6. [DESIGN_CANON.md](internals/DESIGN_CANON.md) · [API_SURFACE.md](guides/API_SURFACE.md) · [MODULE_MAP.md](internals/MODULE_MAP.md)  

Full index: [README.md](README.md)

## Assets model (do not dual-copy)

* Library JS: **`/ux-dom/static/x_element.js`** from installed `ux_dom` (not under `assets/js/` by default).
* App files: **`/assets/*`** → project `assets/`.
* `uxdom serve` / `uxdom dev` do **not** create library JS copies. See DESIGN_CANON §2.

## Quality (maintainers)

```bash
sh scripts/quality.sh
pytest tests/ --cov=ux_dom
```

- [Concurrency](internals/CONCURRENCY.md) — parallel render, tree locks
- [Maintenance canon](ship/MAINTENANCE_CANON.md) — contracts + automation policy

## Profile (DX)

```bash
uxdom profile
```

- [Stack with ux-channel](STACK.md)

## Testing

See [ship/TESTING.md](ship/TESTING.md) and [tests/README.md](../tests/README.md).
