# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ■プロジェクトコンセプト

@README.md を参照してください。

## ■コミュニケーションルール

- 日本語で会話してください
- 進め方を計画してユーザーと認識を合わせてから、実装を進めてください
- 現在の作業状況は @tmp/active_context.md に記録してください
- ユーザーからプロンプトの追加情報で @tmp/current_prompt.md が渡されることがあります
- 動作確認などに必要な一時的なファイルは tmp/ ディレクトリ配下に出力してください

### 重要

- ファイルの文字コードは**UTF-8**を使用してください
- bugfixでユーザーとやり取りする内容はサンプルです。 **決してハードコーディングしないでください**
- ユーザーに提示する前に可能な限りの動作確認、テストを実施してください

## ■開発ルール

### 進め方

- 設計 -> ユーザーと仕様を認識合わせ -> TDDで実装を進める

### 設計方針

- C4モデルで構造を整理
- USMでユースケースを整理
- ユースケースごとにドメインモデリング
  - ドメインモデル図: 具体的な値をオブジェクト図で表現
  - クラス図: ドメインモデルのクラス構造を表現
- DDDに従う
- 図解にはmermaidを利用
  - C4モデルは、mermaid graph記法
    - 図解に説明は含めないでください
    - 説明は markdown tableで、要素名、説明のレイアウトで記載してください

### レイヤー構造と依存関係

```
ユースケース層 → アダプター層 → 外部ライブラリ
     ↓              ↓              ↓
  直接利用        直接実装      mockでテスト
```

- **プレゼンテーション層**: src/main/ (CLIエントリーポイント)
- **ユースケース層**: src/usecase/ (アダプター層を直接利用)
- **ドメイン層**: src/domain/ (ビジネスロジック)
- **アダプター層**: src/adapter/ (外部ライブラリとの実装)

**重要**: リポジトリ層のインターフェースは使用せず、アダプター層を直接利用する

> **TODO（将来対応）**: 本来はリポジトリ層（インターフェース）経由にしたい。
> 現状はユースケース層がアダプター層を直接利用しているが、ドメイン層に
> リポジトリインターフェースを定義し、アダプター層をその実装として
> 差し替える構成へ移行する。移行時は上記の「重要」記述とテスト戦略の
> 該当箇所も更新すること。

### テスト戦略

#### アダプター層のテスト

- **対象**: 外部ライブラリとの連携ロジック
- **Mock対象**: 外部ライブラリのみ（Graphiti、Unstructured.io等）
- **例**: `GraphitiEpisodeRepository`, `UnstructuredDocumentParser`

#### ユースケース層のテスト

- **対象**: ビジネスロジック全体
- **Mock対象**: 外部ライブラリのみ
- **利用**: アダプター層を直接利用した結合テスト
- **メリット**: より実際に近いテストが可能

#### ドメイン層のテスト

- **対象**: ドメインロジック
- **Mock対象**: なし（純粋な単体テスト）

### 開発支援

- rye: パッケージ管理と仮想環境の構築
- pytest: テストフレームワーク
- qlty: コード品質チェックツール(linter, formatter, static analyzer)

### 実装完了時の確認

実装タスク完了時は **必ず `make check`** を実行してからユーザーに提示してください。

```bash
make check
```

これによって以下が実行されます：

1. `make fmt` - コードフォーマット
2. `make lint` - コード品質チェック
3. `make test` - テスト実行

すべてが正常に完了することを確認してから、実装完了を報告してください。

### 決定した内容は @DEVELOPER.md に記録してください

## ■MCP Server運用コマンド

### MCP Server起動・管理

```bash
# MCP Server起動（バックグラウンド）
make docker-up

# 動作状況確認
docker compose ps

# ログ確認
docker compose logs graphiti-mcp --tail 20

# 停止
docker compose down
```

### MCP機能確認

```bash
# n8n.AI Agent設定例
# MCP Server URL: http://localhost:8000/sse
# Transport: SSE
# 利用可能なMCP Tools（search_memory_facts 等）

# 実際のMCP Tools使用確認は n8n.AI Agent から実行
```

### 重要な運用注意事項

- **統合起動**: `make docker-up`でNeo4j + MCP Server同時起動
- **FastMCP使用**: StandardMCPではなくFastMCPサーバーを使用
- **SSE Transport固定**: stdioは使用不可、SSE（Server-Sent Events）のみサポート
- **n8n.AI Agent推奨**: 直接的なPythonクライアントは技術的制約があり、n8n等のMCP対応クライアント使用を推奨
- **環境変数統合**: LLM_MODEL_KEY → OPENAI_API_KEY などの自動マッピング実装済み

## ■開発コマンド

### Makefileが操作の起点

日常操作は基本的に `Makefile` のターゲット経由で行う（`make help` で一覧）。
主要ターゲット:

| ターゲット                                               | 内容                                      |
| -------------------------------------------------------- | ----------------------------------------- |
| `make setup`                                             | 開発環境の初期セットアップ                |
| `make test` / `make test-unit` / `make test-integration` | テスト（`test`は統合テスト除外）          |
| `make check`                                             | fmt + lint + test（**実装完了時に必須**） |
| `make run DIR=path/to/docs GROUP_ID=test`                | ローカルでドキュメント登録                |
| `make docker-up` / `make docker-down`                    | 統合環境（Neo4j + MCP Server）の起動/停止 |
| `make docker-dev-up`                                     | Neo4jのみ起動（ローカル開発用）           |
| `make doctor` / `make show-env`                          | 環境診断 / 環境変数表示                   |
| `make deps-update`                                       | 依存関係の更新                            |

単一テストの実行は素のpytestで:
`rye run pytest tests/domain/test_chunk.py::TestChunk::test_method -v`
（pytest設定は `pytest.ini`。`--strict-markers`、`tmp/`は除外）

### プロジェクトセットアップ

```bash
# プロジェクト初期化
rye init

# 依存関係インストール
rye sync

# 仮想環境の有効化
. .venv/bin/activate
```

### テスト実行

```bash
# 全テスト実行
rye run pytest

# 特定のテストファイル実行
rye run pytest tests/test_specific.py

# カバレッジ付きテスト実行
rye run pytest --cov=src --cov-report=html

# 特定のテストメソッド実行
rye run pytest tests/test_file.py::TestClass::test_method
```

### コード品質チェック

```bash
# qltyによる品質チェック
qlty fmt
qlty check
qlty smells

# 自動修正可能な問題を修正
qlty fix

# 特定のファイルのみチェック
qlty check src/specific_file.py
```

**qlty の挙動メモ（ハマりやすい点）**:

- `qlty check`（引数なし／`make lint`）は**差分ベース**。変更した行・ファイルのみ検査するため、既存ファイルを編集すると既存の lint 債務も表面化することがある。引数にファイルを渡すとファイル全体を検査する。
- プラグイン設定は `.qlty/configs/` に置く（例: `.markdownlint.json`、`.yamllint.yaml`）。ルール単位の無効化は `.qlty/qlty.toml` の `[[exclude]]`（`plugins` + `rules` + **`file_patterns` 必須**）で行う。
- 日本語ドキュメント向けに markdown の `MD013`（行長80字）/`MD060`（表スタイル）は無効化済み。
- `mcp_server/**` は vendored のため qlty 対象外（下記）。

### ビルド・パッケージング

```bash
# パッケージビルド
rye build

# 依存関係の更新
rye sync

# 依存関係の確認
rye show --installed
```

### Dockerビルドの注意点（CPU版PyTorch / uv）

`Dockerfile` は `quay.io/unstructured-io/unstructured` をベースにする。重要な落とし穴:

- **ベースイメージ(unstructured)はuvベース構成**。pipは同梱されず、venvは
  `/app/.venv`（`ENV VIRTUAL_ENV=/app/.venv` を設定し `uv pip install --python` で導入）。
- **amd64版ベースは `torch+cu128` と nvidia-\* 約4.3GBをベースレイヤーに同梱**
  している（arm64版には無い）。子レイヤーで`uninstall`してもベースレイヤーの
  バイトは回収できず、イメージサイズ(amd64 ≈ 7.5GB)は縮まない。これは
  旧0.17.9でも同様で**ベースイメージ固有**。slim化はシステム依存
  (poppler/tesseract/libGL)を失うため非推奨。
- **torchはCPU版に固定する**（プロジェクト方針: CPU版でマルチアーキ対応）。
  `requirements.lock` は plain な `torch==2.10.0` を指すが、uvは
  `-r requirements.txt` の再解決でPyPIの **+cu128(CUDA)版** を選び直す
  （pipは `+cpu` を `==2.10.0` の充足扱いにするがuvはローカルバージョンに厳格）。
  これを避けるため Dockerfile では **2パス + constraint** で導入する:
  1. `--index-url https://download.pytorch.org/whl/cpu` で
     `torch==2.10.0+cpu torchvision==0.25.0+cpu` を明示インストール
     （`+cpu` wheelはCPU indexにしか存在しないため確実にCPU版が入る）
  2. `-c torch-cpu.constraints`（+cpu固定）を付けて残りをPyPIから導入
     （導入済みCPU版で充足され、+cu128への置換が起きない）
  - 検証: `docker run --rm --entrypoint /app/.venv/bin/python <image> -c
"import torch; print(torch.__version__, torch.version.cuda)"`
    → `2.10.0+cpu None` になっていること。

ローカルビルドは `make docker-build`（`scripts/container-build.sh`）。
`graphiti-ingest:local`（ルートDockerfile）と `graphiti-mcp-server:local`
（`mcp_server/Dockerfile`）の2イメージをホストアーキ向けにビルドする。

### mcp_server は vendored subproject（getzep/graphiti 流用）

`mcp_server/` は `getzep/graphiti` の MCP Server を流用した独立サブプロジェクト。
**root とは別物**として扱うこと。

- 独自の `pyproject.toml` / `uv.lock` / ruff 設定（single-quote）を持ち、`main.py` + `src/`（マルチモジュール）+ `config/config.yaml`（`${VAR:default}` で .env 展開）構成。起動は `uv run --no-sync main.py`。
- **root の qlty 対象外**（`.qlty/qlty.toml` の `exclude_patterns` に `mcp_server/**`）。upstream 追従のため**独自整形しない**こと（再同期の差分ノイズを避ける）。
- 取り込み元: `getzep/graphiti` タグ `mcp-v1.0.2`（graphiti-core 0.29.2）。ローカル clone は `~/src/github.com/getzep/graphiti`。
- 本プロジェクト固有の改変（config.yaml の env マッピング / openai LLM の base_url 適用 / cross_encoder の配線 / `search_for_rag` 追加 / SSE 固定 / Neo4j）の詳細は @DEVELOPER.md「MCP Server実装詳細」を参照。

**最新化（再同期）手順**: clone を `git fetch --tags` → 新タグの `mcp_server/{src,main.py,config,pyproject.toml}` を取り込み → 上記の本プロジェクト改変を再適用 → `uv lock` → import スモーク + `make docker-up` 疎通で検証。

## ■アーキテクチャ概要

### システム構成

- **登録時**: ingest.py -> unstructured.io -> graphiti lib -> Neo4j
- **検索時**: n8n.AI Agent などの MCP Client -> MCP Server -> graphiti lib -> Neo4j/ollama
  <http://localhost:8000/sse>

### 主要コンポーネント

1. **MCP Server**: Model Context Protocol準拠の検索サーバー（MCP Tools提供）
2. **Graphiti Core**: グラフデータベースとの連携を管理
3. **Unstructured.io**: ドキュメントの解析とチャンク化
4. **Neo4j**: グラフデータベース（Vector DB）
5. **OpenAI API**: LLMとRerankモデル（高性能・高速）
6. **Ollama**: Embeddingモデルのホスティング（日本語対応）

### 外部依存関係

- Neo4j: bolt://localhost:7687
- MCP Server: <http://localhost:8000/sse> （SSE Transport）
- OpenAI LLM: <https://api.openai.com/v1> （推奨：gpt-4o-mini）
- Ollama Embedder: <http://localhost:11434/v1> （kun432/cl-nagoya-ruri-large）
- システムライブラリ: poppler (PDF処理), tesseract-ocr (OCR)

### 登録処理の堅牢化コンポーネント（src/adapter/）

登録パイプラインの「big picture」は、ファイル位置による状態管理（@DEVELOPER.md
参照）とLLM/Embedding呼び出しの堅牢化に集約される。以下は複数ファイルを
読まないと掴みづらい補助コンポーネント:

- `chunk_file_manager.py`: チャンクを `data/input_chunks/{file_hash}/` に
  エピソードJSONとして退避し、`input/ → input_work/ → input_done/` の
  ファイル移動で進捗を表現。**進捗ファイルを持たず、ファイルの場所＝処理状態**。
  途中失敗しても同じコマンドで残存エピソードから再開でき、DB重複を防ぐ。
- `rate_limit_retry_handler.py` / `rate_limit_coordinator.py`: OpenAI APIの
  rate limit対応。retry-afterヘッダー解析＋指数バックオフ。並列ワーカー間で
  待機を協調させる。
- `entity_cache.py`: 同一ファイル内のエンティティをキャッシュ
  （`FileBasedEntityCache`）し、重複生成・並列時の競合を緩和する。
- `logging_utils.py`: ベンチマーク/分析用のログ出力（`scripts/analyze_api_calls.py`
  と連動）。

並列度の指針・実測値はパフォーマンスの知見セクションと @DEVELOPER.md を参照。

## ■テストコードのルール

テストコードは以下のルールに従って作成してください

### テストメソッド命名規則

テスト名と内容はBDDに倣って、「〜の場合、〜であること」という形式で、ビジネス要件を明確に表現してください。

```
test_{対象機能}_{テスト条件}_{期待結果}であること
```

**例：**

```python
def test_models_endpoint_GETリクエストを送信した場合_claude_sonnet_4だけが返されること(self, server_process):
def test_chat_completion_正常なチャットリクエストを送信した場合_回答が得られること(self, server_process, client):
def test_chat_completion_チャットリクエストで無効なAPIキーでリクエストを送信した場合_例外が発生すること(self, server_process):
```

### AAAパターンの実装

すべてのテストメソッドは以下の3つのセクションに明確に分割してください：

- **準備 (Arrange)**: テストに必要なデータ、オブジェクト、モックを設定
- **実行 (Act)**: テスト対象の機能を実行（1つの操作に集中）
- **検証 (Assert)**: 期待される結果と実際の結果を比較・検証

```python
def test_example_テスト条件_期待結果であること(self, fixtures):
    #------------------------------
    # 準備 (Arrange)
    #------------------------------
    # テストデータの設定、モックの準備など

    #------------------------------
    # 実行 (Act)
    #------------------------------
    # テスト対象の機能を実行

    #------------------------------
    # 検証 (Assert)
    #------------------------------
    # 結果の検証とアサーション
```

### テストケースの焦点

- 各テストメソッドは1つの具体的なシナリオに集中する
- 複雑な並行処理や複数の条件を組み合わせたテストは避ける
- 基本的な動作確認を重視し、エッジケースは別のテストで扱う

## ■パフォーマンス最適化の知見

### LLM API選択指針

以下は実際の性能測定に基づく知見です。新しいLLMサービスを検討する際の参考にしてください。

#### 実証済み最適解

```ini
# 最高性能・最安定の構成（実測）
LLM_MODEL_URL=https://api.openai.com/v1    # 直接接続
LLM_MODEL_NAME=gpt-4o-mini                # 1.57秒/回、高精度
```

#### 避けるべき構成（実測済み問題）

```ini
# 問題のある構成例
LLM_MODEL_URL=http://localhost:4000/v1     # claude-code-server（極度の遅延）
LLM_MODEL_URL=http://localhost:11434/v1    # ollama gemma2/4b（遅延・エラー頻発）
LLM_MODEL_URL=https://openrouter.ai/api/v1 # rate limit・フォーマットエラー
```

### フォーマットエラーの原因と対策

#### 主要な原因

1. **Rate Limit**: OpenRouterで高負荷時にフォーマットエラー頻発
2. **モデル品質**: ローカルLLM（ollama gemma2/4b）で不定期エラー
3. **接続不安定**: ネットワーク経由のAPIゲートウェイ

#### 対策

- **直接API接続**: 中間層を避けて安定性確保
- **高品質モデル**: structured outputに対応した実績あるモデル選択
- **エラーハンドリング**: 一部失敗でも処理継続する設計

### 並列処理の最適化

#### ワーカー数の指針

- **3ワーカー**: 標準構成（実測50秒）
- **5ワーカー**: 微改善のみ（実測49秒、1秒短縮）
- **最適値**: ワーカー数 ≤ ファイル数

#### 実測値（7ファイル処理 - 2025-06-15更新）

- **総実行時間**: 381秒（6分21秒）
- **LLM処理**: 21.0%（80秒、平均1.11秒/回、72回）
- **Embedding処理**: 79.0%（301秒、平均4.56秒/回、66回）- 現在のボトルネック
- **成功率**: 100%（PNG画像含む全ファイル形式対応済み）

### 詳細分析リソース

パフォーマンス分析の詳細は以下のファイルを参照：

- `scripts/analyze_api_calls.py`: API呼び出し分析スクリプト
- パフォーマンス知見の蓄積は@DEVELOPER.mdに記録
