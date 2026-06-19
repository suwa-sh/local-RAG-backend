# Graphiti MCP Server (local-RAG-backend)

`getzep/graphiti` の MCP Server（`mcp-v1.0.2` / graphiti-core 0.29.2）を流用し、
local-RAG-backend 用に再構成したナレッジ検索サーバーです。OpenAI 互換エンドポイント
（LLM / Embedding を別 URL で指定可）と SSE transport に対応します。

## 構成

```
mcp_server/
├── main.py                      # エントリポイント（src/ を sys.path に追加して起動）
├── config/config.yaml           # 設定（${VAR:default} で .env を展開）
├── src/
│   ├── graphiti_mcp_server.py   # MCP Server 本体（@mcp.tool 群）
│   ├── config/schema.py         # 設定スキーマ（pydantic-settings + YAML）
│   ├── services/factories.py    # LLM / Embedder / DB クライアント生成
│   ├── services/queue_service.py
│   ├── models/                  # response_types / entity_types
│   └── utils/                   # formatting / utils
├── pyproject.toml / uv.lock     # 依存（uv 管理, graphiti-core>=0.29.2, Neo4j）
└── Dockerfile
```

## upstream からの主な差分（local-RAG-backend 固有）

- `config/config.yaml` を本プロジェクトの .env 変数名にマッピング
  （`${LLM_MODEL_KEY}` / `${LLM_MODEL_URL}` / `${EMBEDDING_*}` / `${NEO4J_*}` / `${GROUP_ID}`）
- `factories.py`: openai LLM に `base_url=api_url` を適用（`LLM_MODEL_URL` を尊重）
- `GraphitiService.initialize()`: `cross_encoder` を `LLM_MODEL_URL` + `RERANK_MODEL_NAME` で配線
- `search_for_rag` ツールを追加、ノード検索ツール名を `search_memory_nodes` に維持
- transport は SSE 固定、Database は Neo4j（falkordb extra は外す）

## 起動

通常はリポジトリルートの docker compose 経由で起動します。

```bash
# リポジトリルートで
make docker-up          # Neo4j + MCP Server
# エンドポイント: http://localhost:8000/sse
```

単体起動（開発時）:

```bash
cd mcp_server
uv sync
uv run --no-sync main.py            # 既定で config/config.yaml を読込
uv run --no-sync main.py --config config/config.yaml --transport sse
```

## MCP Tools

`add_memory` / `search_for_rag` / `search_memory_facts` / `search_memory_nodes` /
`get_entity_edge` / `get_episodes` / `delete_entity_edge` / `delete_episode` /
`clear_graph` / `get_status`

引数の詳細・upstream 由来の変更点は、リポジトリルートの `DEVELOPER.md`（仕様 / ナレッジ検索）
を参照してください。
