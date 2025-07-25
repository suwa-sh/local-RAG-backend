#!/bin/bash
set -eu

# 現在のアーキテクチャを検出
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    PLATFORM="linux/amd64"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    PLATFORM="linux/arm64"
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

# ローカルビルド（現在のアーキテクチャのみ）
echo "Building for $PLATFORM..."

docker build --platform $PLATFORM \
  --tag graphiti-ingest:local \
  .

docker build --platform $PLATFORM \
  --tag graphiti-mcp-server:local \
  ./mcp_server/.

echo "✅ ローカルビルド完了 (platform: $PLATFORM)"
echo "タグ: graphiti-ingest:local, graphiti-mcp-server:local"
