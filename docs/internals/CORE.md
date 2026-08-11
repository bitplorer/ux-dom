# ux-dom core vs plugins (0.1.0+)

## Core (do not plugin-ize)

These are the long-lived surface. Breaking them breaks every app.

| Module | Responsibility |
|--------|----------------|
| `ux_dom.dom.src.dom_tag` | Tag tree, context stack, render |
| `ux_dom.dom.src.ext.Tags` | Attr dialects, control flags, walk-stream |
| `ux_dom.dom.src.component` | Component / Fragment / ReactiveComponent |
| `ux_dom.dom.htmldocument` | HtmlDocument shell |
| `ux_dom.settings.document` | Document / WebAssets factories |
| `ux_dom.response` | HTML / Streaming response adapters |

Public imports::

    from ux_dom import Component, Document, Fragment, ReactiveComponent, WebAssets
    from ux_dom.dom import div, button, ...

## Plugins (swappable)

| Package | Role |
|---------|------|
| `ux_dom.plugins.host` | FastAPIHost — ASGI app + lifespan |
| `ux_dom.plugins.routing` | DirectoryRouting — file routes |
| `ux_dom.plugins.control` | HtmxControl / NullControl |
| `ux_dom.plugins.style` | TailwindStyle / NullStyle |
| `ux_dom.plugins.hmr` | HotReload |
| `ux_dom.plugins.response` | endpoint wrappers |

Compose::

    from pathlib import Path
    from ux_dom.plugins import App
    from ux_dom.plugins.host import FastAPIHost
    from ux_dom.plugins.routing import DirectoryRouting
    from ux_dom.plugins.control import HtmxControl

    api = (
        App(debug=True)
        .use(FastAPIHost(title="MyApp"))
        .use(DirectoryRouting(package_dir=Path(__file__).parent, base_directory="app"))
        .use(HtmxControl(middleware=True))
        .build()
    )

## CLI

```bash
uxdom create-app myapp
uxdom dev myapp.api:api
uxdom plugins
```
