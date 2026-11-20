#!/usr/bin/env bash
# Lokal va GitHub Actions'da bir xil ishlaydigan tekshiruv: lint + format + testlar.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_VERSION="3.12"
VENV="${CI_VENV:-$PWD/.venv-ci}"

step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

if [ ! -x "$VENV/bin/python" ]; then
    step "virtualenv yaratilmoqda ($VENV, Python $PYTHON_VERSION)"
    if command -v uv >/dev/null 2>&1; then
        uv venv --quiet --python "$PYTHON_VERSION" "$VENV"
    else
        "python$PYTHON_VERSION" -m venv "$VENV"
    fi
fi
export VIRTUAL_ENV="$VENV" PATH="$VENV/bin:$PATH"

step "kutubxonalar o'rnatilmoqda"
if command -v uv >/dev/null 2>&1; then
    uv pip install --quiet -r requirements-dev.txt
else
    python -m pip install --quiet -r requirements-dev.txt
fi

step "ruff: lint"
ruff check .

step "ruff: format"
ruff format --check .

step "pytest"
python -m pytest

step "barcha tekshiruvlar o'tdi"
