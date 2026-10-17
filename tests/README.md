# ux-dom tests

| Layer | Name |
|-------|------|
| PyPI / pip | `ux-dom` |
| Import | `ux_dom` |
| CLI | `uxdom` |

## Layout

```text
tests/
  conftest.py · helpers.py · fixtures/
  browser_gate.py          require_browser(): Playwright toolchain gate
  channel_gate.py          require_channel(): ux-channel companion gate
  example_checks.py        shared assertions for the example apps
  browser/                 Playwright harness JS (not pytest modules)
  01_core/                 DOM · Component · membership · render · reactive
  02_document_plugins/     Document · CSP · XElement · UI kit · runtimes
  03_cli_build/            uxdom CLI · build · deploy (routing is ux-compose)
  04_production/           Readiness · production lock · docs integrity
  05_chaos/                Pentest · stress · races · parsing
  06_browser/              Live Chromium: custom elements, xelement_kit, examples
  07_resilience/           Ownership · adversarial input · residual locks
  08_cleanup_pins/         Behaviour pins written before refactors
  09_examples/             Every app under examples/ over HTTP · hygiene guards
```

`pyproject.toml` sets `pythonpath = ["src", ".", "tests"]`, so tests import
`ux_dom`, `examples.<name>` and the helpers above by name. Only tests that
generate a throwaway app in a temp directory put that directory on `sys.path`.

## Run

```bash
poetry run pytest tests/ -q
# CI mode: missing browser toolchain or ux-channel fails instead of skipping
UX_DOM_REQUIRE_BROWSER=1 UX_DOM_REQUIRE_CHANNEL=1 poetry run pytest tests/ -q
```

Browser toolchain (once):

```bash
npm ci --prefix tests/browser
npx --prefix tests/browser playwright install --with-deps chromium
```

ux-channel (pinned):

```bash
pip install "ux-channel @ git+https://github.com/bitplorer/ux-channel.git@f1a93fcf298c97a59fa6538697731e19aac8586d#subdirectory=python"
```

## Conventions

- Numbered packages keep dependency order (core before plugins before production).
- Tests that need ux-channel or the browser call `require_channel()` /
  `require_browser()`: they skip locally, fail in CI.
- `ux_dom.runtime.Channel` (script tags) is not `ux_channel.Channel` (actions);
  see [docs/STACK.md](../docs/STACK.md).
- No reintroduction of `html_elements.js` / `x-component` / `document.messageHandler`.
