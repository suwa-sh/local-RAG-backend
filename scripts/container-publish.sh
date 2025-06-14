#!/bin/bash
readonly HASH=$(git rev-parse --short HEAD)

docker tag suwash/graphiti-ingest:latest suwash/graphiti-ingest:$HASH
docker push suwash/graphiti-ingest:$HASH
docker push suwash/graphiti-ingest:latest

docker tag suwash/graphiti-mcp-server:latest suwash/graphiti-mcp-server:$HASH
docker push suwash/graphiti-mcp-server:$HASH
docker push suwash/graphiti-mcp-server:latest
