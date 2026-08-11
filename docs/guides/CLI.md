# CLI

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** |

**Entry:** `uxdom` (console script) · also `python -m ux_dom`.

## Design overview

The CLI is the **automation layer** for ceremonial project files. Core library
code lives under `src/ux_dom`; the CLI keeps **apps** in lockstep with Document +
FastAPI + DirectoryRouting contracts.

```text
create-app → dev → add → doctor/lint → build [--package] → deploy
```

| Command family | Role |
|----------------|------|
| **create-app** | Greenfield scaffold (default path for new apps) |
| **add** | Generators: component, route, xelement, ui |
| **doctor / lint** | Read-only integrity |
| **build / deploy** | Assets + host hints |
| **dev / profile / dashboard** | Local DX |

**Policy:** generate ceremonial files by default; hand-code only when extending
features or making breaking changes. See [DX.md](DX.md) ·
[MAINTENANCE_CANON.md](../ship/MAINTENANCE_CANON.md) §5.5.

## create-app

```bash
uxdom create-app myapp
uxdom create-app myapp --template shop
uxdom create-app myapp --with-channel
uxdom create-app myapp --no-csp
uxdom create-app myapp --force
```

Generates:

```text
myapp/
  app/
    main.py          # FastAPI + document.mount + DirectoryRouting
    document.py      # Document.use(XElement, Htmx, Csp.auto, …)
    settings.py
    routes/          # file-based pages
    components/      # optional
  assets/            # Tailwind in/out when enabled
  pyproject.toml / requirements (template-dependent)
```

Post-create integrity: `validate_scaffold` / `uxdom doctor`.

## dashboard

Render p95 SVG graphs (no CDN):

```bash
uxdom dashboard
```

→ `reports/dx/dashboard.html`. For control-plane graphs use **`uxchannel dashboard`**.

## profile

First-class DX: **p95 latency + flamegraph** (does not change app source).

```bash
uxdom profile
uxdom profile --out ./reports/p95
uxdom profile --rounds 80 --json
```

Writes:

* `reports/p95/report.html`
* `reports/p95/latency.json` (p50/p95/p99)
* `reports/p95/profile.speedscope.json` → open in https://www.speedscope.app

## doctor

```bash
uxdom doctor
uxdom doctor --path .
```

Checks: imports, Document shell, XElement runtime, CSP contract, scaffold files.

## build / assets

```bash
uxdom build
```

## add (generators)

```bash
uxdom add component Card
uxdom add route settings
uxdom add xelement Badge --kind shadow
uxdom add ui Dialog
```

Prefer these over hand-writing stubs that must match DirectoryRouter / Document
conventions.

## dev

```bash
uxdom dev
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## Quality (maintainers)

```bash
sh scripts/quality.sh
```

## Side-effect policy (0.1+)

| Command | Writes? | Notes |
|---------|---------|--------|
| templates, examples, ui, plugins, doctor, lint | No | Safe anytime |
| profile | Yes (`reports/`) | Metrics only; never mutates app source |
| create-app | Yes | `--yes` confirms only; **`--force` overwrites** |
| add / deploy | Yes | Existing files require `--force` |
| build | Optional CSS; dist only with `--package` | No dual-copy of `x_element.js` by default |
| dev | Optional CSS if `--tailwind` | **Does not** copy library JS into static |

## Implementation map

| Module | Owns |
|--------|------|
| `ux_dom/cli/cli.py` | Typer entry + command wiring |
| `ux_dom/cli/scaffold.py` | create-app templates |
| `ux_dom/cli/adders.py` | add component/route/xelement/ui |
| `ux_dom/cli/doctor.py` | Integrity checks |
| `ux_dom/cli/build.py` / `deploy.py` | Ship helpers |
| `ux_dom/cli/scaffold_check.py` | validate_scaffold |

See [DESIGN_CANON.md](../internals/DESIGN_CANON.md) and [API_SURFACE.md](API_SURFACE.md).
