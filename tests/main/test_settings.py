"""設定のテスト"""

import pytest
from unittest.mock import patch
import os

from src.main.settings import load_config, AppConfig


class TestSettings:
    """設定のテストクラス"""

    def test_load_config_全ての環境変数が設定されている場合_適切な設定が返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        env_vars = {
            "NEO4J_URL": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password",
            "LLM_MODEL_URL": "http://localhost:4000/v1",
            "LLM_MODEL_NAME": "claude-sonnet-4",
            "LLM_MODEL_KEY": "sk-1234",
            "EMBEDDING_MODEL_URL": "http://localhost:11434/v1",
            "EMBEDDING_MODEL_NAME": "kun432/cl-nagoya-ruri-large:latest",
            "EMBEDDING_MODEL_KEY": "dummy",
            "CHUNK_SIZE_MAX": "1500",
            "CHUNK_SIZE_MIN": "150",
            "CHUNK_OVERLAP": "50",
        }

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config()
            # OPENAI_API_KEYが自動設定されることをpatch内で検証
            openai_api_key = os.getenv("OPENAI_API_KEY")

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert isinstance(config, AppConfig)

        # Neo4j設定
        assert config.neo4j.url == "bolt://localhost:7687"
        assert config.neo4j.user == "neo4j"
        assert config.neo4j.password == "password"

        # LLM設定
        assert config.llm.url == "http://localhost:4000/v1"
        assert config.llm.name == "claude-sonnet-4"
        assert config.llm.key == "sk-1234"

        # 埋め込み設定
        assert config.embedding.url == "http://localhost:11434/v1"
        assert config.embedding.name == "kun432/cl-nagoya-ruri-large:latest"
        assert config.embedding.key == "dummy"

        # チャンク設定
        assert config.chunk.max_size == 1500
        assert config.chunk.min_size == 150
        assert config.chunk.overlap == 50

        # OPENAI_API_KEYが自動設定されること
        assert openai_api_key == "sk-1234"

    def test_load_config_チャンク設定が省略されている場合_デフォルト値が使用されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        env_vars = {
            "NEO4J_URL": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password",
            "LLM_MODEL_URL": "http://localhost:4000/v1",
            "LLM_MODEL_NAME": "claude-sonnet-4",
            "LLM_MODEL_KEY": "sk-1234",
            "EMBEDDING_MODEL_URL": "http://localhost:11434/v1",
            "EMBEDDING_MODEL_NAME": "kun432/cl-nagoya-ruri-large:latest",
            "EMBEDDING_MODEL_KEY": "dummy",
            # チャンク設定を省略
        }

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # デフォルト値が使用されること
        assert config.chunk.max_size == 1000
        assert config.chunk.min_size == 100
        assert config.chunk.overlap == 0

    def test_load_config_必須環境変数が不足している場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        # NEO4J_URLを省略
        env_vars = {
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password",
            "LLM_MODEL_URL": "http://localhost:4000/v1",
            "LLM_MODEL_NAME": "claude-sonnet-4",
            "LLM_MODEL_KEY": "sk-1234",
            "EMBEDDING_MODEL_URL": "http://localhost:11434/v1",
            "EMBEDDING_MODEL_NAME": "kun432/cl-nagoya-ruri-large:latest",
            "EMBEDDING_MODEL_KEY": "dummy",
        }

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="必須の環境変数が設定されていません"):
                load_config()

    def test_load_config_複数の必須環境変数が不足している場合_すべてが報告されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        # 複数の環境変数を省略
        env_vars = {
            "NEO4J_USER": "neo4j",
            "LLM_MODEL_URL": "http://localhost:4000/v1",
            "EMBEDDING_MODEL_URL": "http://localhost:11434/v1",
            # NEO4J_URL, NEO4J_PASSWORD, LLM_MODEL_NAME, LLM_MODEL_KEY,
            # EMBEDDING_MODEL_NAME, EMBEDDING_MODEL_KEY を省略
        }

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError) as exc_info:
                load_config()

            error_message = str(exc_info.value)
            assert "NEO4J_URL" in error_message
            assert "NEO4J_PASSWORD" in error_message
            assert "LLM_MODEL_NAME" in error_message
            assert "LLM_MODEL_KEY" in error_message
            assert "EMBEDDING_MODEL_NAME" in error_message
            assert "EMBEDDING_MODEL_KEY" in error_message

    def test_load_config_OPENAI_API_KEYが未設定の場合_LLM_MODEL_KEYと同じ値が設定されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        env_vars = {
            "NEO4J_URL": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password",
            "LLM_MODEL_URL": "http://localhost:4000/v1",
            "LLM_MODEL_NAME": "claude-sonnet-4",
            "LLM_MODEL_KEY": "sk-test-key",
            "EMBEDDING_MODEL_URL": "http://localhost:11434/v1",
            "EMBEDDING_MODEL_NAME": "kun432/cl-nagoya-ruri-large:latest",
            "EMBEDDING_MODEL_KEY": "dummy",
            # OPENAI_API_KEY は設定しない
        }

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch.dict(os.environ, env_vars, clear=True):
            load_config()
            # OPENAI_API_KEYが自動設定されることをpatch内で検証
            openai_api_key = os.getenv("OPENAI_API_KEY")

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # OPENAI_API_KEYがLLM_MODEL_KEYと同じ値に設定されること
        assert openai_api_key == "sk-test-key"

    def test_load_config_OPENAI_API_KEYが既に設定されている場合_上書きされないこと(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        env_vars = {
            "NEO4J_URL": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password",
            "LLM_MODEL_URL": "http://localhost:4000/v1",
            "LLM_MODEL_NAME": "claude-sonnet-4",
            "LLM_MODEL_KEY": "sk-llm-key",
            "EMBEDDING_MODEL_URL": "http://localhost:11434/v1",
            "EMBEDDING_MODEL_NAME": "kun432/cl-nagoya-ruri-large:latest",
            "EMBEDDING_MODEL_KEY": "dummy",
            "OPENAI_API_KEY": "sk-existing-key",  # 既に設定されている
        }

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch.dict(os.environ, env_vars, clear=True):
            load_config()
            # OPENAI_API_KEYが既存の値を維持することをpatch内で検証
            openai_api_key = os.getenv("OPENAI_API_KEY")

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # OPENAI_API_KEYが既存の値を維持すること
        assert openai_api_key == "sk-existing-key"
