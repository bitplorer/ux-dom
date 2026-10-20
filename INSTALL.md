# ux-dom 0.2.0 — Installation

Python **3.14** required. Package layout: `src/ux_dom` (Poetry).

## Poetry (recommended)

```bash
git clone https://github.com/bitplorer/ux-dom.git
cd ux-dom
poetry env use python3.14
poetry install --with dev,test
poetry run python -c "from ux_dom import __version__; print(__version__)"  # 0.2.0
```

## pip / editable

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e ".[fastapi]"
python -c "from ux_dom import __version__; print(__version__)"
```

## What to install

| Goal | Command |
|------|---------|
| Library only | `poetry install` / `pip install -e .` |
| FastAPI apps | `poetry install --extras fastapi` / `pip install -e ".[fastapi]"` |
| ASGI server, Tailwind CSS | Not ux-dom extras: `pip install ux-compose` (`uxcompose serve`, `uxcompose build`) |
| Live morph / regions | `pip install "ux-channel>=0.1.0"` (companion package) |

## Create an app

```bash
pip install ux-compose ux-dom
uxcompose create-app myapp
cd myapp
uxcompose build
uxcompose serve dev app:asgi --host 0.0.0.0 --port 8080
```

Pure-dom health: `uxdom doctor`.


## Example

```bash
cd examples/xelement_kit
PYTHONPATH=../../src:. poetry run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## Source layout

```text
src/ux_dom/     # importable package
tests/          # pytest suite
examples/       # runnable demos
docs/           # developer docs
```
