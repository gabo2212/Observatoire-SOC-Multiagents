#!/usr/bin/env bash
# Download the recommended Cerebellum GGUF into ./models
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ID="${HF_REPO_ID:-deucebucket/Qwen3.6-35B-A3B-Heretic-Cerebellum-GGUF}"
FILENAME="${HF_FILENAME:-Qwen3.6-35B-A3B-Heretic-Cerebellum-v1-Q3_K_M.gguf}"
OUT_DIR="${MODEL_DIR:-$ROOT/models}"
TARGET="$OUT_DIR/$FILENAME"

mkdir -p "$OUT_DIR"
cd "$ROOT"

if [[ -f "$TARGET" ]]; then
  SIZE="$(du -h "$TARGET" | awk '{print $1}')"
  echo "Model already present ($SIZE): $TARGET"
  exit 0
fi

pick_python() {
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    echo "$ROOT/.venv/bin/python"
  else
    echo "python3"
  fi
}

download_with_hf_cli() {
  local hf_bin="$1"
  "$hf_bin" download "$REPO_ID" "$FILENAME" --local-dir "$OUT_DIR"
}

download_with_python() {
  local py
  py="$(pick_python)"
  HF_REPO_ID="$REPO_ID" HF_FILENAME="$FILENAME" HF_LOCAL_DIR="$OUT_DIR" \
    "$py" - <<'PY'
import os
from huggingface_hub import hf_hub_download

path = hf_hub_download(
    repo_id=os.environ["HF_REPO_ID"],
    filename=os.environ["HF_FILENAME"],
    local_dir=os.environ["HF_LOCAL_DIR"],
)
print(f"Downloaded: {path}")
PY
}

echo "Downloading GGUF (~12 GB) from Hugging Face…"
echo "  repo: $REPO_ID"
echo "  file: $FILENAME"
echo "  dest: $OUT_DIR"

if command -v hf >/dev/null 2>&1; then
  download_with_hf_cli hf
elif [[ -x "$ROOT/.venv/bin/hf" ]]; then
  download_with_hf_cli "$ROOT/.venv/bin/hf"
else
  PY="$(pick_python)"
  if ! "$PY" -c "import huggingface_hub" 2>/dev/null; then
    echo "huggingface_hub missing. Install deps first:" >&2
    echo "  pip install -r requirements.txt" >&2
    echo "  # or: bash scripts/setup.sh" >&2
    exit 1
  fi
  download_with_python
fi

if [[ ! -f "$TARGET" ]]; then
  # hf may nest under repo id; flatten if needed
  NESTED="$(find "$OUT_DIR" -type f -name "$FILENAME" | head -n 1 || true)"
  if [[ -n "$NESTED" && "$NESTED" != "$TARGET" ]]; then
    mv -f "$NESTED" "$TARGET"
  fi
fi

if [[ ! -f "$TARGET" ]]; then
  echo "Download finished but $TARGET not found." >&2
  exit 1
fi

echo "Model ready: $TARGET"
