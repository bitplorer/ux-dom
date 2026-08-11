# ux-dom in one page

Low cognitive load: **four layers**, one arrow of dependence.

```text
┌─────────────────────────────────────────────────────────┐
│  4. YOUR APP                                             │
│     routes · components · business logic                 │
│     uxdom create-app · uxdom add · uxdom ui              │
└──────────────────────────▲──────────────────────────────┘
                           │ uses
┌──────────────────────────┴──────────────────────────────┐
│  3. PLUGINS  (App.use — explicit, ordered, swappable)    │
│     Contribution  →  static files + <head>/<body>        │
│     Host          →  FastAPI / ASGI                      │
│     Routing       →  DirectoryRouter (file-based)        │
│     Control       →  HTMX / uxchannel / null           │
│     Style / HMR   →  Tailwind, hot reload                │
└──────────────────────────▲──────────────────────────────┘
                           │ mounts / injects
┌──────────────────────────┴──────────────────────────────┐
│  2. DOCUMENT SHELL                                       │
│     hub.shell_fragments()  →  tags in head/body          │
│     hub.materialize()      →  assets/** on disk          │
│     StaticFiles /assets                                  │
└──────────────────────────▲──────────────────────────────┘
                           │ renders
┌──────────────────────────┴──────────────────────────────┐
│  1. CORE  (stable for decades)                           │
│     Component · dom_tag · XElement · slots · render      │
│     Attribute dialects L0/L1/L2 (not a bug — by design)  │
└─────────────────────────────────────────────────────────┘
```

## What you touch day-to-day

| Want | Do |
|------|-----|
| New app | `uxdom create-app myapp && cd myapp && uxdom dev` |
| New page | `uxdom add route about` |
| Custom element | `uxdom add xelement Counter` |
| UI primitive | `uxdom add ui Button` (ownable copy) |
| Ship | `uxdom build --package` → `dist/` |
| Live regions | `pip install ux-channel` + live template / `UxChannelRuntime` |

## Non-negotiable rules

1. **Core never imports FastAPI/Tailwind/channel** — only plugins do.
2. **Browser surface only via contributions** — `App.use(XElementRuntime())`, not ad-hoc globals.
3. **`[id]` folders stay `[id]` on disk** — FastAPI path becomes `{id}` (Python can't use `{}` in names).
4. **Dual `clean_attribute` is intentional** — L0 HTML vs L1 hypermedia dialects.
5. **Build materializes contributions** — version of `x_element.js` matches installed `ux_dom`.

## Public imports (prefer these)

```python
from ux_dom import Component, Document, WebAssets, __version__
from ux_dom.dom import div, button, XElement, CustomElement, WebComponent
from ux_dom.plugins import (
    App, XElementRuntime, UxChannelRuntime, shell_fragments, get_hub,
)
from ux_dom.plugins.control import HtmxControl
from ux_dom.plugins.host import FastAPIHost
from ux_dom.plugins.routing import DirectoryRouting
from ux_dom.ui import Button, Card  # optional kit
```

Everything else is advanced or internal.


## Why JS is not “imported” like Python

See **[WHY_JS_URL.md](../security/WHY_JS_URL.md)**. Short version: browser needs an HTTP URL; we mount the **installed package directory** once — no dual copy under `assets/`.

## Third-party JS (uxchannel style)

Libraries ship files **inside their package** and either:

1. **Mount** them (`GET /ux-channel/static/*`) and inject tags only → `serve="package_mount"`
2. **Copy** into app WebAssets on `uxdom build` → `serve="webassets"`

```python
App().use(UxChannelRuntime())                   # mount mode (default)
App().use(UxChannelRuntime(serve="webassets"))  # build copies into assets/
```

See [ASSETS.md](../security/ASSETS.md).


## Script tags once

`shell_fragments` dedupes by `src`/`href`. See [SCRIPT_INJECTION.md](../security/SCRIPT_INJECTION.md).
