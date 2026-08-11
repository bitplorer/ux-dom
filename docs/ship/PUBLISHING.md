# Publishing & ecosystem

## Version

- Source tree: **0.1.0** (`ux_dom.__version__`, `pyproject.toml`)
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
pip install "ux-dom[fastapi]"       # app server
pip install "ux-dom[fastapidev]"    # + tailwind + watchfiles
```

## Typed package

`ux_dom/py.typed` is present (PEP 561). Downstream typecheckers can import
`Document`, `Component`, runtimes, etc.

## Quality before release

```bash
sh scripts/quality.sh
```

Must be green: black, ruff, **full-package mypy**, pytest.
