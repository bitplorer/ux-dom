# Static assets — single copy from installed packages

## Principle

**If a library is installed with the app (`pip install ux-dom` / `uxchannel`),
do not keep a second copy under `assets/`.**

| Approach | Verdict |
|----------|---------|
| Serve JS from **site-packages** via StaticFiles mount | **Preferred** — one copy, always matches pip version |
| Copy JS into `assets/` on build | **Worse** for libraries — dual maintain, skew after upgrade |
| App-authored CSS/images under `assets/` | **Correct** — those are not package data |

uxchannel already does this: package `static/` → mount `/ux-channel/static/*` →
`ch.scripts()` tags. ux-dom does the same for XElement and any
`PackageStaticContribution`.

## How it works

```text
pip install ux-dom └── site-packages/ux_dom/scripts/x_element.js   ← only copy

App().use(XElementRuntime())
  ├── document: <script src="/ux-dom/static/x_element.js">
  └── App.build mounts StaticFiles(
        "/ux-dom/static" → site-packages/ux_dom/scripts/
      )
```

ux-channel:

```text
App().use(UxChannelRuntime())   # or channel mounts itself
  tags → /ux-channel/static/ux-channel.js
  files → site-packages/ux_channel/static/   only
```

## What lives under app `assets/`

- Tailwind input/output CSS  
- App images, fonts, **your** JS  

Not library runtimes.

## Build / package

Product CSS minify: `uxcompose build`.

```bash
uxdom build --package
```

- Verifies installed `x_element.js` contract  
- Records package mount prefixes in MANIFEST  
- **Does not** vendor library JS into `dist/` — `requirements.txt` + pip  
- At runtime, mounts resolve from site-packages  

## Escape hatch (usually avoid)

```python
XElementRuntime(serve="webassets")  # copies into assets/ — dual copy
UxChannelRuntime(serve="webassets")
```

Only for air-gapped trees that ship without site-packages (rare; not recommended).

## Third-party libraries

```python
from ux_dom.plugins import static_from_package

App().use(static_from_package(
    "mycharts",
    "mycharts",
    ["runtime.js"],          # mycharts/static/runtime.js
    serve="package_mount",   # default — single copy
))
```

## App folders

App CSS/JS disk layout is **ux-compose** (`ux_compose.WebAssets`).
This package serves **library** JS from site-packages
(`/ux-dom/static/x_element.js`). Do not duplicate pip-owned JS into `assets/`.

## Security: no raw filesystem exposure

Package static is **not** `StaticFiles(directory=package_root)`.

| Unsafe | Safe (current) |
|--------|----------------|
| Mount whole `ux_dom/scripts/` | Register only `x_element.js` |
| Would serve `__init__.py` | 404 for anything not allowlisted |
| Path `../` escapes | Rejected at registration + resolve |

Enforced by `ux_dom.plugins.safe_static`:

- extension allowlist (`.js`, `.css`, fonts, images — **never** `.py`)
- file must sit under its package directory
- URL must match `/ux-dom/static/…`, `/ux-pkg/<name>/static/…`, or `/ux-channel/static/…`
- exact-path routes only (`install_safe_static`)

## uxchannel static JS (special case)

uxchannel **already** packages and serves its JS. Do not invent a second alias.

| Responsibility | Who |
|----------------|-----|
| File on disk | `site-packages/ux_channel/static/*.js` (pip) |
| HTTP bytes | **Channel** `attach` → `GET /ux-channel/static/ux-channel.js` |
| `<script>` tags | Same URLs as `ch.scripts()` |

### Recommended ux-dom wiring

```python
App()
  .use(XElementRuntime())                           # ux-dom safe file route
  .use(UxChannelRuntime(mount_via_ux_dom=False))    # tags only (default)
  .use(FastAPIHost(...))
  ...
app = builder.build()
attach_channel(app)   # channel mounts /ux-channel/static/* from package
```

Document shell:

```python
plugin_head, plugin_body = shell_fragments(get_hub())
# includes XElement + channel script tags
```

**Do not** also put `raw(ch.scripts())` on every page — you would inject twice.

### When would ux-dom serve channel JS?

Only if channel static is **not** mounted:

```python
UxChannelRuntime(mount_via_ux_dom=True)  # SafeStaticFile allowlist for same URLs
```

Still **one copy** on disk (site-packages). ux-dom only adds exact-file routes.

### vs XElement

| | XElement | uxchannel |
|--|----------|-------------|
| Default server | ux-dom `SafeStaticFile` | Channel host mount |
| URL | `/ux-dom/static/x_element.js` | `/ux-channel/static/ux-channel.js` |
| Tags | `XElementRuntime` | `UxChannelRuntime` ≈ `ch.scripts()` |
