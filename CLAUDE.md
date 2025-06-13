# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ■プロジェクトコンセプト

@README.md を参照してください。

## ■コミュニケーションルール

- 日本語で会話してください
- 進め方を計画してユーザーと認識を合わせてから、実装を進めてください
- ファイルの文字コードはUTF-8を使用してください
- 現在の作業状況は @tmp/active_context.md に記録してください
- 動作確認などに必要な一時的なファイルは tmp/ ディレクトリ配下に出力してください

### 重要

- bugfixでユーザーとやり取りする内容はサンプルです。_決してハードコーディングしないでください_

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

## ■開発コマンド

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

### ビルド・パッケージング

```bash
# パッケージビルド
rye build

# 依存関係の更新
rye sync

# 依存関係の確認
rye show --installed
```

## ■アーキテクチャ概要

### システム構成

- **登録時**: ingest.py -> unstructured.io -> graphiti lib -> Neo4j
- **検索時**: n8n.AI Agent -> graphiti server -> Neo4j/ollama
  <http://localhost:4000/v1>

### 主要コンポーネント

1. **Graphiti Core**: グラフデータベースとの連携を管理
2. **Unstructured.io**: ドキュメントの解析とチャンク化
3. **Neo4j**: グラフデータベース（Vector DB）
4. **Ollama**: LLMとEmbeddingモデルのホスティング

### 外部依存関係

- Neo4j: bolt://localhost:7687
- claude-code-server LLM: <http://localhost:4000/v1>
- Ollama Embedder: <http://localhost:11434/v1>
- システムライブラリ: poppler (PDF処理), tesseract-ocr (OCR)

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
LLM_MODEL_NAME=gpt-4o-mini                # 1.24秒/回、高精度
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

#### 実測値（3ファイル処理）

- **総実行時間**: 49-50秒
- **LLM処理**: 30.9%（21秒）
- **Embedding処理**: 69.1%（47秒）- 現在のボトルネック

### 詳細分析リソース

パフォーマンス分析の詳細は以下のファイルを参照：

- `scripts/analyze_api_calls.py`: API呼び出し分析スクリプト
- パフォーマンス知見の蓄積は@DEVELOPER.mdに記録
