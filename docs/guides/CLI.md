# uxdom CLI (pure Document tooling)

> **Diátaxis:** how-to · **Canonical:** `docs/guides/CLI.md` · **Layer:** ux-dom  
> Map: [INDEX.md](../INDEX.md).

**Product lifecycle is not on this CLI.** Use **uxcompose**:

```bash
uxcompose create-app myapp --host auto --level auto
uxcompose serve app:asgi --port 8080
uxcompose deploy --provider docker
uxcompose doctor .
```

See ux-compose `docs/CLI.md` and `docs/FLOW.md`.

---

## What `uxdom` owns

| Command | Role |
|---------|------|
| `doctor` / `info` | Document / package / env health |
| `lint` | Document convention checks |
| `build` | Tailwind / static verify |
| `profile` / `dashboard` | Render p95 / DX graphs |
| `add` | component \| xelement \| ui (pure-dom) |
| `ui` | List UI kit |

```bash
uxdom doctor
uxdom lint
uxdom build
uxdom profile
uxdom add component Card
uxdom add ui Button
```

---

## Not on uxdom

| Concern | Use |
|---------|-----|
| create-app | `uxcompose create-app` |
| serve / dev / start | `uxcompose serve` |
| deploy | `uxcompose deploy` |
| product doctor | `uxcompose doctor` |
