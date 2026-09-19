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
PORT="${PORT:-8080}"
NGL="${N_GPU_LAYERS:-30}"
CTX="${CTX_SIZE:-8192}"

if [[ ! -f "$MODEL" ]]; then
  echo "Missing model: $MODEL"
  echo "Run: bash scripts/download_model.sh"
  exit 1
fi

echo "Starting llama-server"
echo "  model: $MODEL"
echo "  port:  $PORT"
echo "  ngl:   $NGL  (RTX 4080 12GB: try 25-35)"
echo "  ctx:   $CTX"
echo "API: http://127.0.0.1:${PORT}/v1"

exec llama-server \
  --model "$MODEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --n-gpu-layers "$NGL" \
  --ctx-size "$CTX" \
  --jinja \
  --parallel 1 \
  -np 1
