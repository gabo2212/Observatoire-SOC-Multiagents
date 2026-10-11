#!/usr/bin/env bash
# Download a prebuilt llama-server into ./bin (from ggml-org/llama.cpp releases).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="${LLAMA_BIN_DIR:-$ROOT/bin}"
REPO="ggml-org/llama.cpp"
mkdir -p "$BIN_DIR"

resolve_llama_server() {
  if [[ -n "${LLAMA_SERVER:-}" && -x "$LLAMA_SERVER" ]]; then
    echo "$LLAMA_SERVER"
    return 0
  fi
  if [[ -x "$BIN_DIR/llama-server" ]]; then
    echo "$BIN_DIR/llama-server"
    return 0
  fi
  if command -v llama-server >/dev/null 2>&1; then
    command -v llama-server
    return 0
  fi
  return 1
}

if [[ "${FORCE_LLAMA:-0}" != "1" ]] && existing="$(resolve_llama_server 2>/dev/null)"; then
  echo "llama-server already available: $existing"
  export LD_LIBRARY_PATH="$BIN_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export DYLD_LIBRARY_PATH="$BIN_DIR${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
  "$existing" --version 2>/dev/null || true
  exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to download llama-server" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to pick the latest llama.cpp release" >&2
  exit 1
fi

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
WANT_CUDA=0
if command -v nvidia-smi >/dev/null 2>&1; then
  WANT_CUDA=1
fi

# Prefer CUDA on Linux x86_64 with an NVIDIA GPU; otherwise CPU/Metal builds.
ASSET=""
case "$OS" in
  linux)
    case "$ARCH" in
      x86_64|amd64)
        if [[ "$WANT_CUDA" -eq 1 ]]; then
          ASSET="llama-TAG-bin-ubuntu-cuda-12.8-x64.tar.gz"
        else
          ASSET="llama-TAG-bin-ubuntu-x64.tar.gz"
        fi
        ;;
      aarch64|arm64)
        ASSET="llama-TAG-bin-ubuntu-arm64.tar.gz"
        ;;
    esac
    ;;
  darwin)
    case "$ARCH" in
      arm64) ASSET="llama-TAG-bin-macos-arm64.tar.gz" ;;
      x86_64) ASSET="llama-TAG-bin-macos-x64.tar.gz" ;;
    esac
    ;;
esac

if [[ -z "$ASSET" ]]; then
  echo "No prebuilt llama-server asset for $OS/$ARCH." >&2
  echo "Install llama.cpp manually, then ensure llama-server is on PATH." >&2
  echo "Docs: https://github.com/ggml-org/llama.cpp" >&2
  exit 1
fi

echo "Resolving latest ggml-org/llama.cpp build release..."
TAG="$(
  curl -fsSL "https://api.github.com/repos/${REPO}/releases?per_page=20" \
    | python3 -c "
import json, sys
for rel in json.load(sys.stdin):
    tag = rel.get('tag_name') or ''
    if tag.startswith('b') and tag[1:].isdigit():
        print(tag)
        break
else:
    sys.exit('No bNNNN llama.cpp release found')
"
)"
ASSET="${ASSET/TAG/$TAG}"
URL="https://github.com/${REPO}/releases/download/${TAG}/${ASSET}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ARCHIVE="$TMP/$ASSET"

echo "Downloading $URL"
if ! curl -fL --progress-bar -o "$ARCHIVE" "$URL"; then
  if [[ "$ASSET" == *cuda* ]]; then
    echo "CUDA build unavailable; falling back to CPU ubuntu-x64..."
    ASSET="llama-${TAG}-bin-ubuntu-x64.tar.gz"
    URL="https://github.com/${REPO}/releases/download/${TAG}/${ASSET}"
    curl -fL --progress-bar -o "$ARCHIVE" "$URL"
  else
    exit 1
  fi
fi

echo "Extracting into $BIN_DIR"
tar -xzf "$ARCHIVE" -C "$TMP"

FOUND="$(find "$TMP" -type f -name 'llama-server' | head -n 1 || true)"
if [[ -z "$FOUND" ]]; then
  # Newer packages sometimes ship as llama-server.exe only on Windows; keep Linux/mac name.
  FOUND="$(find "$TMP" -type f \( -name 'llama-server' -o -name 'server' \) | head -n 1 || true)"
fi
if [[ -z "$FOUND" ]]; then
  echo "Archive did not contain llama-server. Contents:" >&2
  find "$TMP" -maxdepth 3 -type f | head -n 40 >&2
  exit 1
fi

# Copy binary + sibling shared libs (preserve symlinks — required for soname links).
PKG_DIR="$(dirname "$FOUND")"
mkdir -p "$BIN_DIR"
cp -a "$FOUND" "$BIN_DIR/llama-server"
chmod +x "$BIN_DIR/llama-server"
shopt -s nullglob
for item in "$PKG_DIR"/lib* "$PKG_DIR"/*.dylib; do
  cp -a "$item" "$BIN_DIR/"
done
shopt -u nullglob

echo "Installed: $BIN_DIR/llama-server"
# Resolve libs next to the binary during the version check
export LD_LIBRARY_PATH="$BIN_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export DYLD_LIBRARY_PATH="$BIN_DIR${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
"$BIN_DIR/llama-server" --version 2>/dev/null || true
echo "Tip: export PATH=\"$BIN_DIR:\$PATH\" or use scripts/start_llm.sh (auto-detects ./bin)."
