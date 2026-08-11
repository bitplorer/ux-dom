# Production readiness — ux-dom 0.1

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** |

Companion: [STACK.md](../STACK.md) · channel production: install `ux-channel` separately.

# Production readiness checklist

## Before ship

- [ ] `DEBUG=0` in production env (`Csp.auto()` → prod policy)
- [ ] `uxdom doctor` clean on the app tree
- [ ] `GET /health` monitored
- [ ] HTTPS terminated; CSP headers present on HTML responses
- [ ] Static assets via package allowlist or your CDN — not open filesystem
- [ ] Tailwind built (`minify`) if used
- [ ] No secrets in `document.py` / client-visible templates

## Library maintainers

```bash
sh scripts/quality.sh
# 516+ tests, black, ruff, mypy public surface
```

## Deploy

See [DEPLOY.md](DEPLOY.md). Typical: uvicorn/gunicorn+uvicorn workers behind reverse proxy.
