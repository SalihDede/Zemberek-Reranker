#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE_NAME="google-morphology-gateway"
PORT="${GOOGLE_MORPH_PORT:-8765}"

echo "┌─ Google Morphology Gateway image build ediliyor (linux/amd64)..."
docker build --platform linux/amd64 -f "$ROOT/Google Morfoloji/Dockerfile" -t "$IMAGE_NAME" "$ROOT"
echo "└─ Image hazır."

echo "┌─ Container başlatılıyor (port $PORT)..."
docker run --rm -it --platform linux/amd64 -p "$PORT:8765" "$IMAGE_NAME"
