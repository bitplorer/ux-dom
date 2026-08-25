# Start here — ux-dom

**Audience:** first-time users of this package.
**Promise:** one rendered document in five minutes, then the ownership map.
**Time:** ~5 minutes.

Longer mental model: [docs/START_HERE.md](docs/START_HERE.md).
**Map:** [docs/INDEX.md](docs/INDEX.md).
**Cookbook:** [docs/guides/SNIPPETS.md](docs/guides/SNIPPETS.md).

Python **3.14** required (`pyproject.toml`).

---

## 1. What this layer is (and is not)

**ux-dom renders** HTML/CSS/JS trees. `Document` is the shell. Serialize is
`__render__` / `__async_render__`.

| Owns | Does **not** own |
|------|------------------|
| Tag trees, Document, CSP stamp, package static | Intent / Cap / Result (`ux-channel`) |
| Pure-dom CLI (`uxdom`) | Product actions / MorphState (`ux-behavior`) |
| | Motion plans (`ux-motion`) |
| | Product create-app / build / serve / deploy (`ux-compose`) |
| | Product DirectoryRoutes / WebAssets / Tailwind / HMR |

Product apps: **[ux-compose](https://github.com/bitplorer/ux-compose)** —
`uxcompose create-app | build | serve | deploy`.

---

## 2. Five minutes — pure Document

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install ux-dom
```

```python
from ux_dom import Document
from ux_dom.runtime import XElement, Htmx, Csp
from ux_dom.dom import div, h1

document = Document(head=[], body=[]).use(
    XElement(), Htmx(), Csp.auto()
)
html = document(div(h1("Hi"))).__render__()
print(html)
```

Success: HTML containing `<h1>Hi</h1>` and the Document shell (runtime tags /
CSP as configured).

Pure-dom health:

```bash
uxdom doctor
```

---

## 3. Five minutes — product app (not this CLI)

```bash
pip install ux-compose ux-dom
uxcompose create-app myapp && cd myapp
uxcompose build
uxcompose serve app:asgi --port 8080
```

Do **not** run `uxdom create-app` or `uxdom serve`. Those are not the product path.
Product CSS is `uxcompose build`, not `uxdom build`.

---

## 4. Where next

| Goal | Doc |
|------|-----|
| Install variants (Poetry / extras) | [INSTALL.md](INSTALL.md) · [docs/INSTALL.md](docs/INSTALL.md) |
| Document SSoT | [docs/guides/DOCUMENT.md](docs/guides/DOCUMENT.md) |
| Component / Fragment | [docs/guides/COMPONENTS.md](docs/guides/COMPONENTS.md) |
| Routing as pages | [docs/reference/ROUTING.md](docs/reference/ROUTING.md) |
| XElement | [docs/guides/XELEMENT.md](docs/guides/XELEMENT.md) |
| Ownership law | [docs/internals/SYSTEM.md](docs/internals/SYSTEM.md) |
| Product lifecycle | ux-compose `docs/FLOW.md` |
| Contributor / agent | [CONTRIBUTING.md](CONTRIBUTING.md) · [AGENTS.md](AGENTS.md) |
| Full map | [docs/INDEX.md](docs/INDEX.md) |
