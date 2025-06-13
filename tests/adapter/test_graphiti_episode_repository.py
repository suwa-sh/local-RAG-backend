"""GraphitiEpisodeRepositoryのテスト"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime

from src.adapter.graphiti_episode_repository import GraphitiEpisodeRepository
from src.domain.episode import Episode
from src.domain.group_id import GroupId
from graphiti_core.graphiti import EpisodeType


class TestGraphitiEpisodeRepository:
    """GraphitiEpisodeRepositoryのテストクラス"""

    def test_GraphitiEpisodeRepository初期化_正常なパラメータを指定した場合_インスタンスが作成されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        neo4j_uri = "bolt://localhost:7687"
        neo4j_user = "neo4j"
        neo4j_password = "password"

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch("src.adapter.graphiti_episode_repository.Graphiti") as mock_client:
            repository = GraphitiEpisodeRepository(
                neo4j_uri=neo4j_uri,
                neo4j_user=neo4j_user,
                neo4j_password=neo4j_password,
                llm_api_key="sk-1234",
                llm_base_url="http://localhost:4000/v1",
                llm_model="claude-sonnet-4",
                rerank_model="gpt-4.1-nano",
                embedding_api_key="dummy",
                embedding_base_url="http://localhost:11434/v1",
                embedding_model="ruri-v3-310m",
            )

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert repository is not None
        mock_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_単一のEpisodeを保存した場合_Graphitiに正常に保存されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        episode = Episode(
            name="test.pdf - chunk 0",
            body="Test episode content",
            source_description="Source file: test.pdf",
            reference_time=datetime(2025, 6, 13, 10, 0, 0),
            episode_type="text",
            group_id=GroupId("default"),
        )

        # Graphitiクライアントのモック
        mock_client = AsyncMock()
        mock_client.add_episode = AsyncMock()

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch(
            "src.adapter.graphiti_episode_repository.Graphiti"
        ) as mock_client_class:
            mock_client_class.return_value = mock_client
            repository = GraphitiEpisodeRepository(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
                llm_api_key="sk-1234",
                llm_base_url="http://localhost:4000/v1",
                llm_model="claude-sonnet-4",
                rerank_model="gpt-4.1-nano",
                embedding_api_key="dummy",
                embedding_base_url="http://localhost:11434/v1",
                embedding_model="ruri-v3-310m",
            )
            await repository.save(episode)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        mock_client.add_episode.assert_called_once()
        call_args = mock_client.add_episode.call_args[1]
        assert call_args["name"] == episode.name
        assert call_args["episode_body"] == episode.body
        assert call_args["source_description"] == episode.source_description
        assert call_args["reference_time"] == episode.reference_time
        assert call_args["source"] == EpisodeType.text
        assert call_args["group_id"] == episode.group_id.value

    @pytest.mark.asyncio
    async def test_save_batch_複数のEpisodeを一括保存した場合_すべてのEpisodeが保存されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        episodes = [
            Episode(
                name="test1.pdf - chunk 0",
                body="First episode content",
                source_description="Source file: test1.pdf",
                reference_time=datetime(2025, 6, 13, 10, 0, 0),
                episode_type="text",
                group_id=GroupId("default"),
            ),
            Episode(
                name="test2.pdf - chunk 0",
                body="Second episode content",
                source_description="Source file: test2.pdf",
                reference_time=datetime(2025, 6, 13, 10, 1, 0),
                episode_type="text",
                group_id=GroupId("default"),
            ),
        ]

        mock_client = AsyncMock()
        mock_client.add_episode = AsyncMock()

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch(
            "src.adapter.graphiti_episode_repository.Graphiti"
        ) as mock_client_class:
            mock_client_class.return_value = mock_client
            repository = GraphitiEpisodeRepository(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
                llm_api_key="sk-1234",
                llm_base_url="http://localhost:4000/v1",
                llm_model="claude-sonnet-4",
                rerank_model="gpt-4.1-nano",
                embedding_api_key="dummy",
                embedding_base_url="http://localhost:11434/v1",
                embedding_model="ruri-v3-310m",
            )
            await repository.save_batch(episodes)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert mock_client.add_episode.call_count == 2

        # 各呼び出しの引数を検証
        call_args_list = mock_client.add_episode.call_args_list
        assert call_args_list[0][1]["name"] == episodes[0].name
        assert call_args_list[1][1]["name"] == episodes[1].name

    @pytest.mark.asyncio
    async def test_save_batch_空のリストを指定した場合_何も処理されないこと(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        episodes = []
        mock_client = AsyncMock()
        mock_client.add_episode = AsyncMock()

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch(
            "src.adapter.graphiti_episode_repository.Graphiti"
        ) as mock_client_class:
            mock_client_class.return_value = mock_client
            repository = GraphitiEpisodeRepository(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
                llm_api_key="sk-1234",
                llm_base_url="http://localhost:4000/v1",
                llm_model="claude-sonnet-4",
                rerank_model="gpt-4.1-nano",
                embedding_api_key="dummy",
                embedding_base_url="http://localhost:11434/v1",
                embedding_model="ruri-v3-310m",
            )
            await repository.save_batch(episodes)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_Graphitiで例外が発生した場合_例外が再発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        episode = Episode(
            name="error.pdf - chunk 0",
            body="Error test content",
            source_description="Source file: error.pdf",
            reference_time=datetime(2025, 6, 13, 10, 0, 0),
            episode_type="text",
            group_id=GroupId("default"),
        )

        mock_client = AsyncMock()
        mock_client.add_episode = AsyncMock(side_effect=Exception("Graphiti error"))

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with patch(
            "src.adapter.graphiti_episode_repository.Graphiti"
        ) as mock_client_class:
            mock_client_class.return_value = mock_client
            repository = GraphitiEpisodeRepository(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
                llm_api_key="sk-1234",
                llm_base_url="http://localhost:4000/v1",
                llm_model="claude-sonnet-4",
                rerank_model="gpt-4.1-nano",
                embedding_api_key="dummy",
                embedding_base_url="http://localhost:11434/v1",
                embedding_model="ruri-v3-310m",
            )

            with pytest.raises(Exception, match="Graphiti error"):
                await repository.save(episode)

    @pytest.mark.asyncio
    async def test_close_クライアントのcloseメソッドが呼ばれること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch(
            "src.adapter.graphiti_episode_repository.Graphiti"
        ) as mock_client_class:
            mock_client_class.return_value = mock_client
            repository = GraphitiEpisodeRepository(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
                llm_api_key="sk-1234",
                llm_base_url="http://localhost:4000/v1",
                llm_model="claude-sonnet-4",
                rerank_model="gpt-4.1-nano",
                embedding_api_key="dummy",
                embedding_base_url="http://localhost:11434/v1",
                embedding_model="ruri-v3-310m",
            )
            await repository.close()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        mock_client.close.assert_called_once()
