# Testing — ux-dom

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** |

## Run the suite

```bash
cd ux-dom
PYTHONPATH=. python -m pytest tests/ -q
```

Layout: [`tests/README.md`](../../tests/README.md).

## Bands

| Band | Folder | Must hold |
|------|--------|-----------|
| Core | `01_core/` | Component, Fragment, render, reactive |
| Document | `02_document_plugins/` | Document, CSP, XElement, package static |
| CLI | `03_routing_cli/` | doctor, lint, add, build (no product scaffold) |
| Production | `04_production/` | Readiness + **production lock** |
| Chaos | `05_chaos/` | Parse / race / pentest |
| Browser | `06_browser/` | Live Chromium when available |

## Production lock

```bash
PYTHONPATH=. python -m pytest tests/04_production/test_production_lock.py -q
```

Peer channel: soft dependency — see [STACK.md](../STACK.md).
