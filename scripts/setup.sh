#!/usr/bin/env bash
# One-shot local setup after cloning: Python env, .env, GGUF model, llama-server.
#
# Usage:
#   bash scripts/setup.sh
#   SKIP_MODEL=1 bash scripts/setup.sh          # deps + llama-server only
#   SKIP_LLAMA=1 bash scripts/setup.sh          # deps + model only
#   FORCE_LLAMA=1 bash scripts/setup.sh         # re-download llama-server into ./bin
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SKIP_MODEL="${SKIP_MODEL:-0}"
SKIP_LLAMA="${SKIP_LLAMA:-0}"
FORCE_LLAMA="${FORCE_LLAMA:-0}"

echo "==> Observatoire SOC — local setup"
echo "    root: $ROOT"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

need_cmd python3

PYTHON_BIN=""
if command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.12)"
else
  PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "$PY_VER" != "3.12" ]]; then
    echo "Python 3.12 is required (CrewAI). Found: $PY_VER" >&2
    echo "Install 3.12 (pyenv/uv/deadsnakes) then re-run this script." >&2
    exit 1
  fi
  PYTHON_BIN="$(command -v python3)"
fi
echo "==> Python: $PYTHON_BIN ($("$PYTHON_BIN" -V))"

echo "==> Virtualenv (.venv)"
if [[ ! -d .venv ]]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv --python "$PYTHON_BIN" .venv
  else
    if ! "$PYTHON_BIN" -m venv .venv; then
      echo "Failed to create .venv. On Debian/Ubuntu install: sudo apt install python3.12-venv" >&2
      exit 1
    fi
  fi
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Python dependencies"
if command -v uv >/dev/null 2>&1; then
  uv pip install -r requirements.txt
else
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
fi

if [[ ! -f .env ]]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
else
  echo "==> .env already present (left unchanged)"
fi

if [[ "$SKIP_LLAMA" != "1" ]]; then
  echo "==> llama-server"
  if [[ "$FORCE_LLAMA" == "1" ]]; then
    rm -f "$ROOT/bin/llama-server"
  fi
  bash "$ROOT/scripts/install_llama_server.sh"
else
  echo "==> Skipping llama-server install (SKIP_LLAMA=1)"
fi

if [[ "$SKIP_MODEL" != "1" ]]; then
  echo "==> GGUF model"
  bash "$ROOT/scripts/download_model.sh"
else
  echo "==> Skipping model download (SKIP_MODEL=1)"
fi

echo
echo "Setup complete."
echo
echo "Next steps:"
echo "  1) source .venv/bin/activate"
echo "  2) bash scripts/start_llm.sh          # terminal 1 — local LLM API"
echo "  3) streamlit run dashboard/app.py     # terminal 2 — dashboard"
echo
echo "Optional offline demo (no LLM):"
echo "  python -m scripts.run_scenario --scenario bruteforce_ssh --offline"
