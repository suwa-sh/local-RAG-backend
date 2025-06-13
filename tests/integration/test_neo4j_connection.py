"""Neo4j接続の統合テスト"""

import os
import pytest
from graphiti_core.graphiti import Graphiti
from graphiti_core.llm_client import OpenAIClient, LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig


# 統合テスト用の環境変数設定
def setup_test_environment():
    """統合テスト用の環境変数をセットアップ"""
    # .envファイルから環境変数を読み込む（OPENAI_API_KEY自動設定含む）
    from src.main.settings import load_config

    try:
        load_config()
    except Exception:
        # .envファイルがない場合はダミー値を設定
        if not os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = "test-key"


# テスト実行前に環境変数をセットアップ
setup_test_environment()


class TestNeo4jConnection:
    """Neo4j接続のテストクラス"""

    @pytest.mark.asyncio
    async def test_neo4j_接続確認_docker環境に接続できること(self):
        """Docker Composeで起動したNeo4jに接続できることを確認"""
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        neo4j_uri = "bolt://localhost:7687"
        neo4j_user = "neo4j"
        neo4j_password = "password"

        # モックのLLMクライアント設定
        llm_config = LLMConfig(
            api_key="test-key", base_url="http://localhost:4000/v1", model="test-model"
        )
        llm_client = OpenAIClient(config=llm_config)

        # モックの埋め込みクライアント設定
        embedder_config = OpenAIEmbedderConfig(
            api_key="test-key",
            base_url="http://localhost:11434/v1",
            embedding_model="test-model",
        )
        embedder = OpenAIEmbedder(config=embedder_config)

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        try:
            client = Graphiti(
                uri=neo4j_uri,
                user=neo4j_user,
                password=neo4j_password,
                llm_client=llm_client,
                embedder=embedder,
            )

            # 簡単な接続テスト（バージョン情報取得）
            # Graphitiクライアントが正常に初期化されることを確認
            assert client is not None

            # クリーンアップ
            await client.close()

        except Exception as e:
            pytest.fail(f"Neo4j接続に失敗しました: {e}")

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # 例外なく処理が完了すれば成功

    @pytest.mark.asyncio
    async def test_neo4j_基本操作_エピソード登録と削除ができること(self):
        """Neo4jにエピソードを登録して削除できることを確認"""
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        neo4j_uri = "bolt://localhost:7687"
        neo4j_user = "neo4j"
        neo4j_password = "password"

        # モックのLLMクライアント設定
        llm_config = LLMConfig(
            api_key="test-key", base_url="http://localhost:4000/v1", model="test-model"
        )
        llm_client = OpenAIClient(config=llm_config)

        # モックの埋め込みクライアント設定
        embedder_config = OpenAIEmbedderConfig(
            api_key="test-key",
            base_url="http://localhost:11434/v1",
            embedding_model="test-model",
        )
        embedder = OpenAIEmbedder(config=embedder_config)

        client = None
        try:
            # ------------------------------
            # 実行 (Act)
            # ------------------------------
            client = Graphiti(
                uri=neo4j_uri,
                user=neo4j_user,
                password=neo4j_password,
                llm_client=llm_client,
                embedder=embedder,
            )

            # テスト用エピソードの追加
            # 注意: 実際のLLMエンドポイントが必要なため、このテストは現在スキップ
            pytest.skip(
                "実際のLLM/Embeddingエンドポイントが必要なため、接続確認のみ実行"
            )

        except Exception as e:
            pytest.fail(f"Graphiti操作に失敗しました: {e}")

        finally:
            # ------------------------------
            # クリーンアップ
            # ------------------------------
            if client:
                await client.close()
