# Contributing

## Setup

```bash
pip install -e ".[fastapidev]"
pip install pytest pytest-cov black ruff mypy
```

## Quality gate (required)

```bash
sh scripts/quality.sh
# or:
black --check ux_dom tests
ruff check ux_dom --select F401,F841,F811,E9,F821
mypy ux_dom --ignore-missing-imports
pytest tests/ -q
```

Coverage: `pytest --cov=ux_dom` (fail_under=70).

## Docs

- Product docs: `docs/` (see `docs/README.md`)
- Do not add new material only to `docs/archive/`
- Keep Document + FastAPI + `document.mount` as the canonical story

## Architecture rules

1. **Document** owns HTML head/body placement  
2. **FastAPI** owns the process  
3. No second document factory on `App`  
4. Prefer `document.use(runtimes)` over hub-only wiring  
