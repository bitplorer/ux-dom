#!/usr/bin/env sh
# UxDom quality gate — fail on regressions, no capability changes.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT"
PY="${PYTHON:-python3}"

echo "== black =="
black --check src/ux_dom tests

echo "== ruff =="
ruff check src/ux_dom --select F401,F841,F811,E9,F821

echo "== mypy (full package) =="
$PY -m mypy src/ux_dom --ignore-missing-imports

echo "== pytest =="
$PY -m pytest tests/ -q --tb=line

if $PY -c "import pytest_cov" 2>/dev/null; then
  echo "== coverage =="
  $PY -m pytest tests/ -q --tb=no --cov=ux_dom --cov-report=term-missing:skip-covered || true
fi

echo "quality OK"
