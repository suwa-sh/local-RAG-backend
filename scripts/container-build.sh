#!/bin/bash
set -eu

# buildxビルダーのセットアップ
docker buildx create --name multiarch --use || docker buildx use multiarch

# マルチアーキテクチャビルド（arm64とamd64）
docker buildx build --platform linux/amd64,linux/arm64 \
  --tag suwash/graphiti-ingest:latest \
  --push \
  .

docker buildx build --platform linux/amd64,linux/arm64 \
  --tag suwash/graphiti-mcp-server:latest \
  --push \
  ./mcp_server/.
