# Ingest Test Fixtures

このディレクトリには、ingest機能の動作確認用テストデータが含まれています。

## ディレクトリ構成

### test_simple/

- **用途**: 基本的な動作確認
- **内容**: シンプルなテキストファイル
- **実行**: `make ingest-simple`

### test_documents/

- **用途**: 複数ファイル・多様な形式での動作確認
- **内容**: 様々なファイル形式のサンプル
- **実行**: `make ingest-example`

## 使用方法

```bash
# シンプルなテスト
make ingest-simple

# サンプルファイルテスト
make ingest-example

# カスタムテスト
make run GROUP=my-test DIR=fixtures/ingest/test_simple
```

## 注意事項

- これらのテストは外部LLM APIを使用するため、適切なAPIキー設定が必要です
- 統合テストではなく、手動での動作確認用です
- 処理時間はLLMモデルの性能に依存します
