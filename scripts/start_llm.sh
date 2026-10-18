#!/usr/bin/env bash
# Start llama-server for the Heretic Cerebellum GGUF (OpenAI-compatible API)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

MODEL="${GGUF_PATH:-$ROOT/models/Qwen3.6-35B-A3B-Heretic-Cerebellum-v1-Q3_K_M.gguf}"
# Allow relative GGUF_PATH from .env
if [[ "$MODEL" != /* ]]; then
  MODEL="$ROOT/$MODEL"
fi
PORT="${PORT:-8080}"
NGL="${N_GPU_LAYERS:-30}"
CTX="${CTX_SIZE:-8192}"

resolve_llama_server() {
  if [[ -n "${LLAMA_SERVER:-}" && -x "$LLAMA_SERVER" ]]; then
    echo "$LLAMA_SERVER"
    return 0
  fi
  if [[ -x "$ROOT/bin/llama-server" ]]; then
    echo "$ROOT/bin/llama-server"
    return 0
  fi
  if command -v llama-server >/dev/null 2>&1; then
    command -v llama-server
    return 0
  fi
  return 1
}

if [[ ! -f "$MODEL" ]]; then
  echo "Missing model: $MODEL"
  echo "Run: bash scripts/setup.sh"
  echo "  or: bash scripts/download_model.sh"
  exit 1
fi

if ! LLAMA_BIN="$(resolve_llama_server)"; then
  echo "llama-server not found."
  echo "Run: bash scripts/install_llama_server.sh"
  echo "  or: bash scripts/setup.sh"
  exit 1
fi

echo "Starting llama-server"
echo "  binary: $LLAMA_BIN"
echo "  model:  $MODEL"
echo "  port:   $PORT"
echo "  ngl:    $NGL  (RTX 4080 12GB: try 25-35)"
echo "  ctx:    $CTX"
echo "API: http://127.0.0.1:${PORT}/v1"

# Prefer project bin libs when CUDA packages dropped .so next to the binary
export LD_LIBRARY_PATH="$ROOT/bin${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export DYLD_LIBRARY_PATH="$ROOT/bin${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"

exec "$LLAMA_BIN" \
  --model "$MODEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --n-gpu-layers "$NGL" \
  --ctx-size "$CTX" \
  --jinja \
  --parallel 1 \
  -np 1
