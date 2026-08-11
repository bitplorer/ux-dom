# ux-dom tests (0.1)

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-dom` |
| **Import** | `ux_dom` |
| **CLI** | **`uxdom`** |

## Layout

```text
tests/
  helpers.py / conftest.py / fixtures/
  browser/                 Playwright harness JS (not pytest modules)
  01_core/                 DOM · Component · membership · render · reactive
  02_document_plugins/     Document · CSP · XElement · UI kit · plugins
  03_routing_cli/          Router · scaffold · CLI · build · deploy
  04_production/           Hardening · readiness · examples · **0.1 lock**
  05_chaos/                Pentest · stress · races · parsing
  06_browser/              Live Chromium (kit, xelement, auth)
```

## Run

```bash
PYTHONPATH=. python -m pytest tests/ -q
# focused production lock
PYTHONPATH=. python -m pytest tests/04_production/test_production_0_1_lock.py -q
```

## Conventions

- Numbered packages keep **dependency order** (core before plugins before production).
- Peer **ux-channel** is optional; tests that need it soft-import / skip.
- `UxChannelRuntime` ≠ `ux_channel.Channel` — see [docs/STACK.md](../docs/STACK.md).
- No reintroduction of `html_elements.js` / `x-component` / `document.messageHandler`.
