# ux-dom core vs plugins (0.1.0+)

## Core (do not plugin-ize)

These are the long-lived surface. Breaking them breaks every app.

| Module | Responsibility |
|--------|----------------|
| `ux_dom.dom.src.dom_tag` | Tag tree, context stack, render |
| `ux_dom.dom.src.ext.Tags` | Attr dialects, control flags, walk-stream |
| `ux_dom.dom.src.component` | Component / Fragment / ReactiveComponent |
| `ux_dom.dom.htmldocument` | HtmlDocument shell |
| `ux_dom.settings.document` | Document factory (app folders → `ux_compose.WebAssets`) |
| `ux_dom.response` | HTML / Streaming response adapters |

Public imports::

    from ux_dom import Component, Document, Fragment, ReactiveComponent
    from ux_dom.dom import div, button, ...

## Plugins

Control and response helpers stay useful for pure Document trees:

| Package | Role |
|---------|------|
| `ux_dom.plugins.control` | HtmxControl / NullControl |
| `ux_dom.plugins.response` | endpoint wrappers |

Product host, product routing, Tailwind compiler, HotReload, and app asset
folders are **not** taught from this package. They fail closed or redirect:

| Concern | Product home |
|---------|--------------|
| Page routes | `ux_compose.routing.DirectoryRoutes` |
| App CSS folders | `ux_compose.WebAssets` |
| Tailwind CLI | `uxcompose build` (`ux_compose.tailwind`) |
| Serve / HMR / tunnel | `uxcompose serve` |
| Scaffold | `uxcompose create-app` |

## CLI

```bash
# product
uxcompose create-app myapp
uxcompose build
uxcompose serve app:asgi --port 8080

# pure-dom tooling
uxdom doctor
uxdom lint
uxdom profile
```

See [SYSTEM.md](SYSTEM.md) and ux-compose `docs/FLOW.md`.
