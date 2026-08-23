# Contributing

**First-time:** [START_HERE.md](START_HERE.md). **Map:** [docs/INDEX.md](docs/INDEX.md). **Agent contract:** [AGENTS.md](AGENTS.md).

## Setup

Python **3.14**. Package layout: `src/ux_dom` (Poetry).

```bash
pip install -e ".[fastapidev]"
pip install pytest pytest-cov black ruff mypy toml
```

Poetry:

```bash
poetry env use python3.14
poetry install --with dev,test --extras fastapidev
```

See [INSTALL.md](INSTALL.md).

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
Docs links: `pytest tests/04_production/test_docs_integrity.py -q`.

## Automation-first

Ceremonial **product** files are produced by **`uxcompose`**. Pure-dom stubs
(`add component|xelement|ui`) stay on **`uxdom`**.

| Do | Don't |
|----|-------|
| `uxcompose create-app` for product apps | Re-handwrite a second product scaffold in ux-dom |
| `uxdom add component\|ui\|xelement` | Copy-paste drift from examples as a second scaffold |
| Update compose generators when the *product template* should change | Patch only one example and leave CLI stale |
| Put new teaching in the matching Diátaxis slot ([docs/INDEX.md](docs/INDEX.md)) | Mix tutorial steps into reference pages |

Core library changes (`src/ux_dom`) always need tests + the matching guide
under `docs/`. See [AGENTS.md](AGENTS.md) and [docs/guides/DX.md](docs/guides/DX.md).

## Docs

Layer law (what a file may contain):

| File | May contain | Must not contain |
|------|-------------|------------------|
| `README.md` | Gate: definition, ownership, install, one example, links | Full API, long tutorials, ADR bodies |
| `START_HERE.md` | 5-minute first success | Exhaustive reference |
| `docs/guides/` | Goal-oriented recipes | Conceptual essays as primary form |
| `docs/internals/` | Why / architecture | Step lists as primary form |
| `CHANGELOG.md` | History | Current teaching of deleted APIs as live |

Rules:

- Index: [docs/INDEX.md](docs/INDEX.md) · audience table: [docs/README.md](docs/README.md)
- Nested paths only (`guides/`, `internals/`, `security/`, `ship/`) — gated by
  `tests/04_production/test_docs_integrity.py`
- Do not add new material only to `docs/archive/`
- Keep Document + FastAPI + `document.mount` as the canonical story
- Fix broken links and stale test paths in the same PR as the change
- Do not invent public names; `__init__.py` wins

## Architecture rules

1. **Document** owns HTML head/body placement
2. **FastAPI** owns the process (when used as an adapter; product host is ux-compose)
3. No second document factory on `App`
4. Prefer `document.use(runtimes)` over hub-only wiring
5. Prefer package-mounted library JS (`/ux-dom/static/…`) over dual-copy into `/assets`

## Pull requests

- Feature branches. Never commit directly to `main`. Never force-push `main`.
- Docs-only changes still run `test_docs_integrity`.
- One concern per PR when practical.
