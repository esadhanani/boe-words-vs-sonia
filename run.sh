#!/bin/sh
# Full pipeline. Downloads are cached in data/raw (pass --refresh to re-download).
set -e
cd "$(dirname "$0")"
PY=${PY:-.venv/bin/python}
$PY -I src/fetch.py "$@"
$PY -I src/parse.py
$PY -I src/score.py > /dev/null
$PY -I src/market.py
$PY -I src/analyse.py
$PY -I -m pytest -q tests
