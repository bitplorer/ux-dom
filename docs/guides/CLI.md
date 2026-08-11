# CLI

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** |

**Entry:** `uxdom` (console script) · also `python -m ux_dom`.

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
```

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

See [DESIGN_CANON.md](../internals/DESIGN_CANON.md) and [API_SURFACE.md](API_SURFACE.md).
