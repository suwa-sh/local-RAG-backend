# local-RAG-backend

**v0.1.0** - 高性能なローカルRAGドキュメント登録システム

ローカル環境で完結するRAGシステムのバックエンドです。28種類のファイル形式をサポートし、並列処理により高速な文書登録を実現します。

## ✨ 特徴

- **高速並列処理**: 3-5ワーカーで並列実行（約50秒で3ファイル処理）
- **28種類ファイル対応**: PDF、Office、テキスト、画像など幅広いファイル形式
- **本格運用対応**: 設定管理、エラーハンドリング、テストカバレッジ完備
- **DDD設計**: ドメイン駆動設計による保守性の高いアーキテクチャ

## 🏗️ システム構成

### 登録処理（v0.1.0実装済み）

```
CLI → ユースケース層 → アダプター層 → 外部ライブラリ
                    ├── Unstructured.io (文書解析)
                    ├── Graphiti (グラフDB操作)
                    └── Neo4j (データ保存)
```

### 検索処理（v0.2.0予定）

```
n8n.AI Agent → Graphiti Server → Neo4j + Ollama
```

## 🚀 クイックスタート

### 1. 環境セットアップ

```bash
# 開発環境構築
make setup

# 環境変数設定
make env-example
# .envファイルを編集して適切な値を設定

# Neo4j起動
make docker-up
```

### 2. 動作確認

```bash
# テスト実行
make test

# 実際のファイルで動作確認
make ingest-simple
```

## 📄 ドキュメント登録

### 基本的な使い方

```bash
# 標準実行（3ワーカー並列処理）
PYTHONPATH=. rye run python -m src.main.ingest <group_id> <directory>

# ワーカー数指定
PYTHONPATH=. rye run python -m src.main.ingest <group_id> <directory> --workers 5
```

### Makefileでの実行

```bash
# 基本的な実行
make run GROUP=my-group DIR=/path/to/documents
make run GROUP=my-group DIR=/path/to/documents WORKERS=5  # ワーカー数指定

# テスト・サンプル実行
make ingest-simple               # シンプルテスト
make ingest-example              # サンプル実行

# パフォーマンス測定（ログ記録・分析付き）
make ingest-benchmark            # 3ワーカー、約50秒
make ingest-benchmark-fast       # 5ワーカー、約49秒

# ログ分析
make analyze-performance
```

### パフォーマンス調整

| ワーカー数 | 適用場面   | 実行時間（3ファイル） |
| ---------- | ---------- | --------------------- |
| 1          | デバッグ時 | 約3分                 |
| 3（推奨）  | 標準利用   | 約50秒                |
| 5          | 高速化重視 | 約49秒                |

## 🔍 検索機能（v0.2.0予定）

```bash
# 検索API（未実装）
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "検索したい内容",
    "group_ids": ["default"],
    "max_facts": 10
  }'
```

## ⚙️ 設定

### 環境変数

#### 推奨設定（実証済み高性能構成）

```ini
# Neo4jデータベース
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# LLMモデル（最高性能：1.24秒/回）
LLM_MODEL_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
LLM_MODEL_KEY=your_openai_api_key

# Embeddingモデル（ローカル推論）
EMBEDDING_MODEL_URL=http://localhost:11434/v1
EMBEDDING_MODEL_NAME=kun432/cl-nagoya-ruri-large:latest
EMBEDDING_MODEL_KEY=dummy

# チャンク設定（最適化済み）
CHUNK_SIZE_MAX=2000
CHUNK_SIZE_MIN=200
CHUNK_OVERLAP=0
```

#### ⚠️ 避けるべき設定

```ini
# 以下の設定は実測で問題が確認されています
LLM_MODEL_URL=http://localhost:4000/v1     # claude-code-server（遅延大）
LLM_MODEL_URL=http://localhost:11434/v1    # ollama LLM（エラー頻発）
LLM_MODEL_URL=https://openrouter.ai/api/v1 # rate limit問題
```

### サポートファイル形式（28種類）

| カテゴリ             | 対応形式                             |
| -------------------- | ------------------------------------ |
| **テキスト**         | txt, md, rst, org                    |
| **Web**              | html, xml                            |
| **PDF**              | pdf                                  |
| **Microsoft Office** | doc, docx, ppt, pptx, xls, xlsx      |
| **OpenDocument**     | odt                                  |
| **リッチテキスト**   | rtf                                  |
| **eBook**            | epub                                 |
| **データ**           | csv, tsv                             |
| **メール**           | eml, msg, p7s                        |
| **画像**             | bmp, heic, jpeg, jpg, png, tiff, tif |

## 🧪 テスト・品質管理

### テスト種類

| コマンド                | 対象                             | 実行時間 | 説明                    |
| ----------------------- | -------------------------------- | -------- | ----------------------- |
| `make test`             | ユニット・結合テスト（85テスト） | 約2秒    | 外部API不要の高速テスト |
| `make test-integration` | Neo4j接続テスト                  | 約10秒   | インフラ接続確認        |
| `make ingest-simple`    | E2Eテスト                        | 約30秒   | 実際のAPI使用           |

### 品質チェック

```bash
# コード品質総合チェック
make check              # format + lint + test

# 個別実行
make fmt               # コードフォーマット
make lint              # 静的解析
make test-cov          # カバレッジ付きテスト
```

### 開発フロー

```bash
# 1. 基本品質チェック
make test

# 2. インフラ接続確認
make test-integration

# 3. 実機能確認
make ingest-example

# 4. パフォーマンス分析
make ingest-benchmark
make analyze-performance
```

## 📊 パフォーマンス

### 実測値（3ファイル処理）

- **実行時間**: 49-50秒（並列処理）
- **処理内訳**: LLM 30.9%、Embedding 69.1%
- **スループット**: 約6ファイル/分
- **91%高速化**: 9分→50秒（初期シーケンシャル処理比）

### ボトルネック分析

1. **Embeddingモデル**: kun432/cl-nagoya-ruri-large（3.13秒/回）
2. **LLMモデル**: OpenAI GPT-4o mini（1.24秒/回）- 高速
3. **並列度**: 3ワーカーが最適（3ファイル処理時）

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 実行が遅い・エラーが多発する場合

1. **LLM設定の確認**

   ```bash
   # 推奨設定に変更
   LLM_MODEL_URL=https://api.openai.com/v1
   LLM_MODEL_NAME=gpt-4o-mini
   ```

2. **フォーマットエラーが頻発する場合**

   - OpenRouter使用時: 直接API接続に変更
   - ローカルLLM使用時: 外部APIに変更

3. **パフォーマンス分析**

   ```bash
   # 実行時間とボトルネック分析
   make ingest-benchmark
   make analyze-performance
   ```

#### API設定のベストプラクティス

- **OpenAI API**: 最も安定・高速（推奨）
- **ローカルLLM**: 実用性に課題あり
- **APIゲートウェイ**: rate limit問題のリスク

詳細な分析は `scripts/analyze_api_calls.py` を使用してください。

## 🗺️ ロードマップ

### v0.1.0（実装完了）

- ✅ ドキュメント登録機能（28ファイル形式対応）
- ✅ 高速並列処理（91%性能改善）
- ✅ 本格運用対応（設定管理・エラーハンドリング・テスト）

### v0.2.0（予定）

- 🔄 検索API機能（Graphiti Server経由）

### v1.0.0（将来）

- 🔄 パフォーマンス監視（langfuse連携）
