# =============================================================================
# local-RAG-backend Makefile
# =============================================================================

# .envファイルが存在する場合は読み込む
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

.PHONY: help setup test test-unit test-integration lint fmt check clean run ingest docker-build docker-publish docker-up docker-down doctor

# デフォルトターゲット
help: ## ヘルプメッセージを表示
	@echo "local-RAG-backend 開発コマンド"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_\/-]+:.*?## / {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# =============================================================================
# 開発環境セットアップ
# =============================================================================

setup: ## 開発環境の初期セットアップ
	@echo "🔧 開発環境セットアップ中..."
	rye sync
	@echo "✅ 依存関係インストール完了"
	@echo ""
	@echo "次のステップ:"
	@echo "  1. make docker-up    # Neo4jを起動"
	@echo "  2. make env-example  # 環境変数設定"
	@echo "  3. make test         # テスト実行"

env-example: ## .env.exampleファイルを.envにコピー
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env ファイルを作成しました"; \
		echo "📝 .env ファイルを編集して適切な値を設定してください"; \
	else \
		echo "⚠️  .env ファイルは既に存在します"; \
	fi

# =============================================================================
# テスト関連
# =============================================================================

test: ## 全テストを実行（統合テスト除く）
	@echo "🧪 テスト実行中..."
	rye run pytest tests/ --ignore=tests/integration/ --tb=short

test-unit: ## ユニットテストのみ実行
	@echo "🧪 ユニットテスト実行中..."
	rye run pytest tests/domain/ tests/adapter/ tests/usecase/ tests/main/ -v

test-integration: ## 統合テストを実行
	@echo "🧪 統合テスト実行中..."
	@echo "⚠️  Neo4jとLLMエンドポイントが起動している必要があります"
	rye run pytest tests/integration/ -v

test-cov: ## カバレッジ付きテスト実行
	@echo "🧪 カバレッジ付きテスト実行中..."
	rye run pytest tests/ --ignore=tests/integration/ \
		--cov=src --cov-report=html --cov-report=term

test-watch: ## テストをwatch モードで実行
	@echo "🧪 テストwatch モード開始..."
	rye run pytest tests/ --ignore=tests/integration/ -f

# =============================================================================
# コード品質
# =============================================================================

lint: ## コード品質チェック
	@echo "🔍 コード品質チェック中..."
	qlty check

fmt: ## コードフォーマット
	@echo "🎨 コードフォーマット中..."
	qlty fmt

check: fmt lint test ## リント + テストを実行

# =============================================================================
# Docker関連
# =============================================================================
docker-build: ## ローカルDockerイメージをビルド
	@echo "🐳 ローカルDockerイメージビルド中..."
	./scripts/container-build.sh
	@echo "✅ ローカルイメージビルド完了"

docker-up: ## 統合環境を起動（Neo4j + MCP Server）
	@echo "🐳 統合環境起動中..."
	docker compose up -d
	@echo "✅ 統合環境起動完了"
	@echo "🌐 Neo4jブラウザ: http://localhost:7474"
	@echo "🌐 MCP Server: http://localhost:8000/sse"

docker-down: ## 統合環境を停止
	@echo "🐳 統合環境停止中..."
	docker compose down

docker-logs: ## Dockerログを表示
	docker compose logs -f

docker-clean: ## Dockerデータを完全削除
	@echo "⚠️  全データが削除されます"
	@read -p "続行しますか? [y/N]: " confirm && [ "$$confirm" = "y" ]
	docker compose down -v
	rm -rf data/*
	@echo "✅ データ削除完了"

## 開発環境用Docker
docker-dev-up: ## 開発環境を起動（Neo4jのみ）
	@echo "🐳 開発環境起動中..."
	docker compose -f docker-compose.dev.yml up -d
	@echo "✅ 開発環境起動完了（Neo4jのみ）"
	@echo "🌐 Neo4jブラウザ: http://localhost:7474"

docker-dev-down: ## 開発環境を停止
	@echo "🐳 開発環境停止中..."
	docker compose -f docker-compose.dev.yml down

docker-up-local: ## ローカルビルドイメージで統合環境を起動
	@echo "🐳 ローカルイメージで統合環境起動中..."
	docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
	@echo "✅ 統合環境起動完了（ローカルイメージ使用）"
	@echo "🌐 Neo4jブラウザ: http://localhost:7474"
	@echo "🌐 MCP Server: http://localhost:8000/sse"

## Dockerでのドキュメント登録
docker-ingest: ## Dockerでドキュメント登録（data/input/配下を処理）
	@echo "📄 Dockerでドキュメント登録実行中..."
	@echo "  入力ディレクトリ: ./data/input/"
	@echo "  グループID: $${GROUP_ID:-default}"
	docker compose run --rm ingest
	@echo "✅ 登録完了"
	@echo "📊 ログ確認: tail -f data/logs/ingest-*.log"

# =============================================================================
# ドキュメント登録（ingest）
# =============================================================================

## 基本的な使い方
run: ## ドキュメント登録実行（例: make run DIR=path/to/docs GROUP_ID=test）
	@if [ -z "$(DIR)" ]; then \
		echo "❌ DIR を指定してください"; \
		echo "例: make run DIR=/path/to/documents GROUP_ID=my-group"; \
		exit 1; \
	fi
	@echo "📄 ドキュメント登録実行中..."
	@echo "  グループID: $${GROUP_ID:-環境変数から取得}"
	@echo "  ディレクトリ: $(DIR)"
	@echo "  ワーカー数: $${WORKERS:-3}（デフォルト）"
	@if [ -n "$$GROUP_ID" ]; then \
		GROUP_ID=$$GROUP_ID rye run python -m src.main.ingest $(DIR) $${WORKERS:+--workers $$WORKERS}; \
	else \
		rye run python -m src.main.ingest $(DIR) $${WORKERS:+--workers $$WORKERS}; \
	fi

## テスト・サンプル実行
ingest-simple: ## シンプルテスト（fixtures/test_simple/test.txt）
	@echo "📄 シンプルテスト実行中..."
	@echo "✅ テストファイル: fixtures/ingest/test_simple/test.txt"
	$(MAKE) run DIR=fixtures/ingest/test_simple

ingest-example: ## サンプル実行（fixtures/test_documents/）
	@echo "🚀 サンプル実行中..."
	@echo "✅ サンプルファイル: fixtures/ingest/test_documents/"
	$(MAKE) run DIR=fixtures/ingest/test_documents

## パフォーマンス測定・分析
ingest-benchmark: ## ベンチマーク実行（ログ記録・分析付き）
	@mkdir -p logs
	@echo "⚡ ベンチマーク実行中（3ワーカー）..."
	@echo "開始時刻: $$(date)" | tee logs/benchmark.log
	@rye run python -m src.main.ingest fixtures/ingest/test_documents 2>&1 | tee -a logs/benchmark.log
	@echo "終了時刻: $$(date)" | tee -a logs/benchmark.log
	@echo ""
	@echo "📊 パフォーマンス分析実行中..."
	@python scripts/analyze_api_calls.py logs/benchmark.log

analyze-performance: ## 最新のベンチマークログを分析
	@if [ -f logs/benchmark-fast.log ]; then \
		echo "📊 高速ベンチマーク分析中..."; \
		python scripts/analyze_api_calls.py logs/benchmark-fast.log; \
	elif [ -f logs/benchmark.log ]; then \
		echo "📊 標準ベンチマーク分析中..."; \
		python scripts/analyze_api_calls.py logs/benchmark.log; \
	else \
		echo "❌ 分析対象のログファイルが見つかりません"; \
		echo "   実行: make ingest-benchmark または make ingest-benchmark-fast"; \
	fi

# =============================================================================
# 開発支援
# =============================================================================

doctor: ## 環境診断
	@echo "🩺 環境診断中..."
	@echo ""
	@echo "📦 Python環境:"
	@python --version
	@echo ""
	@echo "📦 Rye環境:"
	@rye --version
	@echo ""
	@echo "🐳 Docker環境:"
	@docker --version
	@docker compose version
	@echo ""
	@echo "📊 Neo4j接続確認:"
	@if docker compose ps | grep -q "local-rag-neo4j.*healthy"; then \
		echo "✅ Neo4j: 起動中"; \
		docker exec local-rag-neo4j cypher-shell -u $${NEO4J_USER:-neo4j} -p $${NEO4J_PASSWORD:-password} \
			"MATCH (n) RETURN count(n) as nodes;" 2>/dev/null || echo "⚠️  Neo4j: 接続エラー"; \
	else \
		echo "❌ Neo4j: 停止中"; \
		echo "   実行: make docker-up"; \
	fi
	@echo ""
	@echo "🌐 LLMエンドポイント確認:"
	@if curl -s $${LLM_MODEL_URL:-http://localhost:4000}/v1/models -H "Authorization: Bearer $${LLM_MODEL_KEY:-sk-1234}" > /dev/null 2>&1; then \
		echo "✅ LLM: $${LLM_MODEL_URL:-http://localhost:4000} 接続OK"; \
	else \
		echo "❌ LLM: $${LLM_MODEL_URL:-http://localhost:4000} 接続失敗"; \
	fi
	@echo ""
	@echo "🔤 Embeddingエンドポイント確認:"
	@if curl -s $${EMBEDDING_MODEL_URL:-http://localhost:11434}/v1/models > /dev/null 2>&1; then \
		echo "✅ Embedding: $${EMBEDDING_MODEL_URL:-http://localhost:11434} 接続OK"; \
	else \
		echo "❌ Embedding: $${EMBEDDING_MODEL_URL:-http://localhost:11434} 接続失敗"; \
	fi

neo4j-query: ## Neo4jに直接クエリ実行（例: make neo4j-query QUERY="MATCH (n) RETURN n LIMIT 5"）
	@if [ -z "$(QUERY)" ]; then \
		echo "❌ QUERYを指定してください"; \
		echo "例: make neo4j-query QUERY=\"MATCH (n) RETURN count(n)\""; \
		exit 1; \
	fi
	docker exec local-rag-neo4j cypher-shell -u $${NEO4J_USER:-neo4j} -p $${NEO4J_PASSWORD:-password} "$(QUERY)"

neo4j-browser: ## Neo4jブラウザURLを開く（macOS）
	@echo "🌐 Neo4jブラウザを開いています..."
	@echo "URL: http://localhost:7474"
	@echo "ユーザー名: $${NEO4J_USER:-neo4j}"
	@echo "パスワード: $${NEO4J_PASSWORD:-password}"
	@if command -v open >/dev/null 2>&1; then \
		open http://localhost:7474; \
	else \
		echo "ブラウザで http://localhost:7474 を開いてください"; \
	fi

show-env: ## 現在の環境変数設定を表示
	@echo "🔧 環境変数設定:"
	@echo "GROUP_ID=${GROUP_ID}"
	@echo "NEO4J_URI=${NEO4J_URI}"
	@echo "LLM_MODEL_URL=${LLM_MODEL_URL}"
	@echo "EMBEDDING_MODEL_URL=${EMBEDDING_MODEL_URL}"
	@if [ -f .env ]; then \
		echo ""; \
		echo "📄 .env ファイル内容:"; \
		cat .env | grep -v "^#" | grep -v "^$$"; \
	else \
		echo ""; \
		echo "⚠️  .env ファイルが見つかりません"; \
		echo "   実行: make env-example"; \
	fi

# =============================================================================
# その他
# =============================================================================

deps-update: ## 依存関係を更新
	@echo "📦 依存関係更新中..."
	rye sync --update-all
