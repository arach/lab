#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${1:-arach/local-intelligence-eval:latest}"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BUILD_TOOL="${BUILD_TOOL:-}"

cd "$ROOT_DIR"

if [[ -z "$BUILD_TOOL" ]]; then
  if command -v container >/dev/null 2>&1; then
    BUILD_TOOL="container"
  elif command -v docker >/dev/null 2>&1; then
    BUILD_TOOL="docker"
  else
    echo "No supported image builder found. Install Apple's container CLI or Docker."
    exit 1
  fi
fi

case "$BUILD_TOOL" in
  container)
    container build --progress plain -t "$IMAGE_NAME" -f eval/local_intelligence/Dockerfile .
    ;;
  docker)
    docker build -f eval/local_intelligence/Dockerfile -t "$IMAGE_NAME" .
    ;;
  *)
    echo "Unsupported BUILD_TOOL: $BUILD_TOOL"
    echo "Use BUILD_TOOL=container or BUILD_TOOL=docker"
    exit 1
    ;;
esac

echo "Built $IMAGE_NAME"
echo "Next steps:"
echo "  push the image to a registry HF Jobs can read"
echo "  python3 eval/local_intelligence/launch_hf_job.py --image $IMAGE_NAME ..."
