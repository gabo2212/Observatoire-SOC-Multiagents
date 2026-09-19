#!/usr/bin/env bash
# Download the recommended Cerebellum GGUF into ./models
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/models"
cd "$ROOT"
hf download deucebucket/Qwen3.6-35B-A3B-Heretic-Cerebellum-GGUF \
  Qwen3.6-35B-A3B-Heretic-Cerebellum-v1-Q3_K_M.gguf \
  --local-dir models
echo "Model ready: $ROOT/models/Qwen3.6-35B-A3B-Heretic-Cerebellum-v1-Q3_K_M.gguf"
