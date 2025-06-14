#!/bin/bash
docker build --tag suwash/graphiti-ingest:latest .

docker build --tag suwash/graphiti-mcp-server:latest ./mcp_server/.
