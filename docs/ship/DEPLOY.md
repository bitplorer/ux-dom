# Deploy

App entry is ASGI: `app.main:app` after create-app.

# ux-dom build & deploy

ux-dom apps are **ASGI** services (usually FastAPI + uvicorn).  
There is no proprietary ux-dom cloud — `uxdom deploy` **prepares** host configs; you publish with that host’s CLI/CI.

## Static JS shipping

See **[ASSETS.md](../security/ASSETS.md)**. Short version (single-copy model):

* `x_element.js` lives only in the **installed** `ux_dom` package
* Browser URL: **`/ux-dom/static/x_element.js`** (package mount via `document.use(XElement())`)
* `uxdom build` **verifies** the package file — it does **not** dual-copy into app `assets/`
* Use `--package` to emit a runnable `dist/` tree (app code + requirements; pip supplies library JS)

Escape hatch only: `XElementRuntime(serve="webassets")` materializes under `assets/js/`.

## `uxdom build`

Runs from a **create-app** project root (`app/main.py`):

1. Checks `app/main.py` + installed package `x_element.js` contract
2. Records package mount URLs (no dual-copy by default)
3. Runs `python -m app.tailwindcss` when present (production CSS)
4. Imports `app.main:app` in a subprocess (fail closed)
5. Soft `doctor --prod` notes (e.g. DEBUG still True)

```bash
cd myapp
uxdom build
uxdom build --skip-tailwind
uxdom build --package              # dist/<app>/ with assets + run.sh
uxdom build --archive --name myapp # dist/myapp.tar.gz
uxdom build --json
```

Exit code **0** only if all hard steps pass.

## `uxdom deploy`

**Does not** push images or call cloud APIs (no secrets in the CLI).

```bash
uxdom deploy --provider docker      # Dockerfile + .dockerignore
uxdom deploy -p fly --name my-app   # fly.toml (+ Dockerfile)
uxdom deploy -p render              # render.yaml
uxdom deploy -p railway             # railway.json
uxdom deploy -p vps                 # systemd unit under deploy/
uxdom deploy -p checklist           # print-only go-live list
uxdom deploy -p docker --force      # overwrite
```

### ASGI contract (every provider)

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

### Env checklist

| Variable | Notes |
|----------|--------|
| `DEBUG` | `false` in production |
| `SECRET_KEY` / app secret | From host secrets, not git |
| `PORT` | Render/Railway/Fly inject this |
| `UX_CHANNEL_*` | Only if using ux-channel |

### Recommended flow

```bash
uxdom doctor
uxdom build
uxdom deploy -p docker
docker build -t myapp . && docker run -p 8080:8080 -e DEBUG=false myapp
```

## What about Vercel?

Vercel is optimized for Node/serverless frontends. ux-dom is a long-lived **Python ASGI** process (streaming HTML, WS/SSE-friendly). Prefer:

- **Docker** on Fly / Render / Railway / Cloud Run / ECS  
- **VPS** + systemd + Caddy  

If you must use serverless Python, you need an adapter and will lose some streaming/WS patterns — not the default path.

## CI sketch

```yaml
# .github/workflows/build.yml (sketch)
- run: pip install -e ".[fastapi]"
- run: uxdom build --skip-tailwind   # or with tailwind binary in CI
- run: pytest
```


Plugin JS: see [ASSETS.md](../security/ASSETS.md) (`ux_dom.assets` registry + WebAssets.sync_plugin_assets).
