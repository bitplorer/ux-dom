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

Next.js-shaped day-1 surface:

```text
create-app ≈ create-next-app
dev        ≈ next dev          (reload + Tailwind --watch)
serve      ≈ next dev | start  (default dev; --prod for start)
start      ≈ next start        (no reload, minify CSS)
build      ≈ next build
lint       ≈ next lint
doctor / info ≈ next info
```

```text
create-app → serve / dev → add → doctor/lint → build [--package] → start / deploy
```

| Command family | Role |
|----------------|------|
| **create-app** | Greenfield scaffold (default path for new apps) |
| **add** | Generators: component, route, xelement, ui |
| **doctor / info / lint** | Read-only integrity |
| **build / deploy** | Assets + host hints |
| **dev / serve / start** | Process runner + standalone Tailwind CLI |
| **profile / dashboard** | Local DX |

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

## serve / dev / start

```bash
uxdom serve                 # dev: reload + Tailwind --watch
uxdom serve --port 8080
uxdom serve --prod          # production
uxdom start                 # alias of serve --prod
uxdom dev                   # alias of serve (dev)
uxdom serve --no-tailwind --no-reload
```

**Standalone Tailwind CLI** (first hit wins):

1. `UXDOM_TAILWIND` / `TAILWINDCSS`
2. `tailwindcss` on PATH
3. `pytailwindcss` extra (`pip install pytailwindcss`)
4. local `node_modules` (`@tailwindcss/cli`)
5. cached official binary under `$XDG_CACHE_HOME/ux-dom/`
6. download official standalone (`v4.1.12`; disable with `UXDOM_TAILWIND_DOWNLOAD=0`)
7. last resort: `npx --yes @tailwindcss/cli`

`.env`, `.env.local`, `.env.development` / `.env.production` load automatically
(process env wins). HMR is the create-app `WITH_HMR` lifespan plugin — `serve`
does not copy library JS.

When `serve` owns CSS it sets `UXDOM_TAILWIND_OWNED=1` so in-app `TailwindStyle`
does not start a second watcher.

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

## doctor / info

```bash
uxdom doctor
uxdom doctor --path .
uxdom info                  # Next-style alias
```

Checks: imports, Document shell, XElement runtime, Tailwind CLI resolver, CSP contract, scaffold files.

## build / assets

```bash
uxdom build
```

Compiles CSS via the same standalone Tailwind resolver as `serve`.

## add (generators)

```bash
uxdom add component Card
uxdom add route settings
uxdom add xelement Badge --kind shadow
uxdom add ui Dialog
```

Prefer these over hand-writing stubs that must match DirectoryRouter / Document
conventions.

## Quality (maintainers)

```bash
sh scripts/quality.sh
```

## Side-effect policy (0.1+)

| Command | Writes? | Notes |
|---------|---------|--------|
| templates, examples, ui, plugins, doctor, info, lint | No | Safe anytime |
| profile | Yes (`reports/`) | Metrics only; never mutates app source |
| create-app | Yes | `--yes` confirms only; **`--force` overwrites** |
| add / deploy | Yes | Existing files require `--force` |
| build | Optional CSS; dist only with `--package` | No dual-copy of `x_element.js` by default |
| serve / dev | CSS via standalone Tailwind; no library JS copy | `--no-tailwind` to skip |
| start | Minify CSS then serve | Production alias of `serve --prod` |

## Implementation map

| Module | Owns |
|--------|------|
| `ux_dom/cli/cli.py` | Typer entry + command wiring |
| `ux_dom/cli/serve.py` | `serve` / `dev` / `start` process runner |
| `ux_dom/cli/tailwind.py` | Standalone Tailwind CLI resolver |
| `ux_dom/cli/envfile.py` | Next-style `.env*` loading |
| `ux_dom/cli/scaffold.py` | create-app templates |
| `ux_dom/cli/adders.py` | add component/route/xelement/ui |
| `ux_dom/cli/doctor.py` | Integrity checks |
| `ux_dom/cli/build.py` / `deploy.py` | Ship helpers |
| `ux_dom/cli/scaffold_check.py` | validate_scaffold |

See [DESIGN_CANON.md](../internals/DESIGN_CANON.md) and [API_SURFACE.md](API_SURFACE.md).
