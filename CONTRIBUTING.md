# Contributing

## Setup

```bash
pip install -e ".[fastapidev]"
pip install pytest pytest-cov black ruff mypy toml
```

## Quality gate (required)

```bash
sh scripts/quality.sh
# or:
black --check src/ux_dom tests
ruff check src/ux_dom --select F401,F841,F811,E9,F821
mypy src/ux_dom --ignore-missing-imports
pytest tests/ -q
```

Coverage: `pytest --cov=ux_dom` (fail_under=70).

## Automation-first

Ceremonial **product** files are produced by **`uxcompose`**. Pure-dom stubs
(`add component|xelement|ui`) stay on **`uxdom`**.

| Do | Don't |
|----|-------|
| `uxcompose create-app` for product apps | Re-handwrite a second product scaffold in ux-dom |
| `uxdom add component\|ui\|xelement` | Copy-paste drift from examples as a second scaffold |
| Update compose generators when the *product template* should change | Patch only one example and leave CLI stale |

Core library changes (`src/ux_dom`) always need tests + the matching guide
under `docs/`. See [AGENTS.md](AGENTS.md) and [docs/guides/DX.md](docs/guides/DX.md).

## Docs

- Product docs: `docs/` (index: `docs/README.md`)
- Design / architecture: `docs/internals/ARCHITECTURE.md`, `DESIGN_CANON.md`, `MODULE_MAP.md`
- Nested paths only (`guides/`, `internals/`, `security/`, `ship/`) — integrity gated by
  `tests/04_production/test_docs_integrity.py`
- Do not add new material only to `docs/archive/`
- Keep Document + FastAPI + `document.mount` as the canonical story
- Fix broken links and stale test paths in the same PR as the change

## Architecture rules

1. **Document** owns HTML head/body placement
2. **FastAPI** owns the process
3. No second document factory on `App`
4. Prefer `document.use(runtimes)` over hub-only wiring
5. Prefer package-mounted library JS (`/ux-dom/static/…`) over dual-copy into `/assets`
