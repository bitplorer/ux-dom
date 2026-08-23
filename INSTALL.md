# ux-dom 0.1.0 — Installation

Python **3.14** required. Package layout: `src/ux_dom` (Poetry).

## Poetry (recommended)

```bash
git clone https://github.com/bitplorer/ux-dom.git
cd ux-dom
poetry env use python3.14
poetry install --with dev,test --extras fastapidev
poetry run python -c "from ux_dom import __version__; print(__version__)"  # 0.1.0
```

## pip / editable

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e ".[fastapidev]"
python -c "from ux_dom import __version__; print(__version__)"
```

## What to install

| Goal | Command |
|------|---------|
| Library only | `poetry install` / `pip install -e .` |
| FastAPI apps | `poetry install --extras fastapi` / `pip install -e ".[fastapi]"` |
| FastAPI + Tailwind + HMR | `poetry install --extras fastapidev` / `pip install -e ".[fastapidev]"` |
| Live morph / regions | `pip install "ux-channel>=0.1.0"` (companion package) |

## Create an app

```bash
pip install ux-compose ux-dom
uxcompose create-app myapp
cd myapp
uxcompose serve app:asgi --host 0.0.0.0 --port 8080
```

Pure-dom health: `uxdom doctor`.


## Showcase example

```bash
cd examples/standalone_showcase
PYTHONPATH=../../src:. poetry run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## Source layout

```text
src/ux_dom/     # importable package
tests/          # pytest suite
examples/       # runnable demos
docs/           # developer docs
```
