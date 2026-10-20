# Publishing & ecosystem

## Version

- Source tree: **0.2.0** (`ux_dom.__version__`, `pyproject.toml`)
- PyPI may lag; install from this source until the cut is published.

## Build & publish (maintainers)

```bash
pip install build twine
python -m build
twine check dist/*
# twine upload dist/*
```

## Extras consumers should install

```bash
pip install "ux-dom[fastapi]"       # FastAPI + Starlette responses
```

Server, Tailwind and scaffold come from ux-compose, not from ux-dom extras:

```bash
pip install ux-compose
```

## Typed package

`ux_dom/py.typed` is present (PEP 561). Downstream typecheckers can import
`Document`, `Component`, runtimes, etc.

## Quality before release

```bash
sh scripts/quality.sh
```

Must be green: black, ruff, **full-package mypy**, pytest.
