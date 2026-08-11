# Test coverage

## How to measure

```bash
pip install pytest-cov
pytest tests/ --cov=ux_dom --cov-report=term-missing
```

## Policy (`pyproject.toml`)

| Setting | Value |
|---------|--------|
| **fail_under** | **70%** |
| **omit** | `dom/ui.py`, `elements/*`, `examples/*`, demo CLI glue, alpinejs |

Omits avoid punishing large tag tables / experimental UI while keeping the
hypermedia spine honest.

## Baseline (0.1.0)

| Metric | Value |
|--------|--------|
| Tests | **536 passed**, 6 skipped |
| Line coverage (with omits) | **~75.7%** |
| Gate | `fail_under = 70` — green |
| Full-package mypy | clean |

## Priority if you raise further

1. `settings/commands.py` (Tailwind CLI)  
2. `cli/cli.py` (Typer commands not all smoke-tested)  
3. `reloader/*`, `assets/*`  
4. `utils/functional.py`  

## Related bug fixed while covering

Dataclass `Component` init chain used `id(cls)` memoization; CPython reuses ids
after GC, so long suites could skip wrapping → empty `str(Component())`. Fixed
to key off the wrapped `__init__` flag only.
