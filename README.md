# local-RAG-backend

localで完結するRAGのバックエンドです。

## 構成(仮)

- 登録時
  - ingest.py
    - unstructured.io
      - poppler
      - tesseract-ocr
    - garaphiti lib
      - Neo4j
- 検索時
  - n8n.AI Agent Node ※管理外
    - graphiti server
      - Neo4j
      - ollama
        - llm model
        - embedding model

## 利用方法

- 登録時

  ```sh
  # ingest.py <group_id> <directory>
  ingest.py default /path/to/dir/
  ```

- 検索時
  - 指定グループ内の検索

    ```sh
    curl -X POST http://localhost:8000/search \
      -H "Content-Type: application/json" \
      -d '{
        "query": "検索したい内容",
        "group_ids": ["default"],
        "max_facts": 10
      }'
    ```

  - すべてのグループの検索

    ```sh
    curl -X POST http://localhost:8000/search \
      -H "Content-Type: application/json" \
      -d '{
        "query": "検索したい内容",
        "max_facts": 10
      }'
    ```

## 環境変数

```ini
LLM_MODEL_URL=http://localhost:4000/v1
LLM_MODEL_NAME=claude-sonnet-4
LLM_MODEL_KEY=sk-1234

EMBEDDING_MODEL_URL=http://localhost:11434/v1
EMBEDDING_MODEL_NAME=kun432/cl-nagoya-ruri-large:latest
EMBEDDING_MODEL_KEY=dummy
```

## 計画

- v0.1.0
  - 指定ディレクトリ配下のファイル群をナレッジ登録できる
  - 検索APIを提供し、登録したナレッジを検索できる
- v1.0.0
  - 検索時の内部処理を、langfuseでモニタリングできる
    - graphitiに実装がないので、pythonのloggingハンドラーで本体に外付けで実装予定
