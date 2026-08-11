# DX overview

## Goals

- **Low cognitive load:** one document model, one ASGI host.
- **Scaffold parity** with Vue/CRA: `uxdom create-app`.
- **Batteries optional:** HTMX, XElement, CSP, Tailwind, uxchannel via flags.

## Day-1 commands

```bash
uxdom create-app myapp
uvicorn app.main:app --reload
uxdom doctor
uxdom add component Card
```

## What good DX looks like here

| Surface | Experience |
|---------|------------|
| Document.use | Explicit runtimes, ordered |
| document.mount | One call for static + middleware |
| DirectoryRouter | File = route |
| Csp.auto | Zero-choice secure default |
| Component + dataclass | Natural Python |

## Avoid

- Building HTML via `App.web` as if it were the document
- Manual custom-element definition lists (auto-collect)
- Copying library JS into `/assets` by hand (package static allowlist)

## Quality gate

`sh scripts/quality.sh` — [START_HERE.md](../START_HERE.md)
