"""GraphitiEpisodeRepositoryのテスト"""

import pytest
from unittest.mock import patch, AsyncMock, Mock
from datetime import datetime

from src.adapter.graphiti_episode_repository import GraphitiEpisodeRepository
from src.domain.episode import Episode
from src.domain.group_id import GroupId
from graphiti_core.graphiti import EpisodeType
from graphiti_core.llm_client.errors import RateLimitError


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
                rate_limit_max_retries=3,
                rate_limit_default_wait_time=121,
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

    @pytest.mark.asyncio
    async def test_save_RateLimitErrorが発生した場合_リトライされること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        episode = Episode(
            name="rate_limit.pdf - chunk 0",
            body="Rate limit test content",
            source_description="Source file: rate_limit.pdf",
            reference_time=datetime(2025, 6, 13, 10, 0, 0),
            episode_type="text",
            group_id=GroupId("default"),
        )

        # RateLimitErrorのモック（retry-afterヘッダー付き）
        mock_response = Mock()
        mock_response.headers = {"retry-after": "2"}
        mock_original_error = Exception("Original error")
        mock_original_error.response = mock_response

        # RateLimitErrorを作成し、__cause__を直接設定
        rate_limit_error = RateLimitError("Rate limit exceeded")
        rate_limit_error.__cause__ = mock_original_error

        # 1回目はエラー、2回目は成功
        mock_client = AsyncMock()
        mock_client.add_episode = AsyncMock(side_effect=[rate_limit_error, None])

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch(
            "src.adapter.graphiti_episode_repository.Graphiti"
        ) as mock_client_class:
            with patch("asyncio.sleep") as mock_sleep:
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
                    rate_limit_max_retries=3,
                    rate_limit_default_wait_time=121,
                )
                await repository.save(episode)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert mock_client.add_episode.call_count == 2
        mock_sleep.assert_called_once_with(3)  # 2秒 + 1秒のバッファ

    @pytest.mark.asyncio
    async def test_save_RateLimitErrorで最大リトライ回数を超えた場合_例外が発生すること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        episode = Episode(
            name="rate_limit_max.pdf - chunk 0",
            body="Rate limit max retry test",
            source_description="Source file: rate_limit_max.pdf",
            reference_time=datetime(2025, 6, 13, 10, 0, 0),
            episode_type="text",
            group_id=GroupId("default"),
        )

        # RateLimitErrorのモック（デフォルト待機時間）
        rate_limit_error = RateLimitError("Rate limit exceeded")

        # 常にエラー
        mock_client = AsyncMock()
        mock_client.add_episode = AsyncMock(side_effect=rate_limit_error)

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with patch(
            "src.adapter.graphiti_episode_repository.Graphiti"
        ) as mock_client_class:
            with patch("asyncio.sleep") as mock_sleep:
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
                    rate_limit_max_retries=3,
                    rate_limit_default_wait_time=121,
                )

                with pytest.raises(RateLimitError):
                    await repository.save(episode)

        # リトライ回数分呼ばれることを確認（初回 + 3回リトライ = 4回）
        assert mock_client.add_episode.call_count == 4
        assert mock_sleep.call_count == 3  # 3回リトライ時の待機

    @pytest.mark.asyncio
    async def test_save_RateLimitError以外のエラーの場合_リトライされないこと(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        episode = Episode(
            name="other_error.pdf - chunk 0",
            body="Other error test",
            source_description="Source file: other_error.pdf",
            reference_time=datetime(2025, 6, 13, 10, 0, 0),
            episode_type="text",
            group_id=GroupId("default"),
        )

        # 通常のエラー
        other_error = ValueError("Some other error")
        mock_client = AsyncMock()
        mock_client.add_episode = AsyncMock(side_effect=other_error)

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with patch(
            "src.adapter.graphiti_episode_repository.Graphiti"
        ) as mock_client_class:
            with patch("asyncio.sleep") as mock_sleep:
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
                    rate_limit_max_retries=3,
                    rate_limit_default_wait_time=121,
                )

                with pytest.raises(ValueError):
                    await repository.save(episode)

        # リトライなしで1回のみ呼ばれる
        assert mock_client.add_episode.call_count == 1
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_RateLimitErrorとIndexErrorが混在した場合_独立してリトライされること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        episode = Episode(
            name="mixed_error.pdf - chunk 0",
            body="Mixed error test content",
            source_description="Source file: mixed_error.pdf",
            reference_time=datetime(2025, 6, 13, 10, 0, 0),
            episode_type="text",
            group_id=GroupId("default"),
        )

        # RateLimitErrorのモック
        mock_response = Mock()
        mock_response.headers = {"retry-after": "1"}
        mock_original_error = Exception("Original error")
        mock_original_error.response = mock_response
        rate_limit_error = RateLimitError("Rate limit exceeded")
        rate_limit_error.__cause__ = mock_original_error

        mock_client = AsyncMock()
        # IndexError → RateLimitError → RateLimitError → 成功
        mock_client.add_episode = AsyncMock(
            side_effect=[
                IndexError("list index out of range"),  # 1回目: IndexError
                rate_limit_error,  # 2回目: RateLimitError
                rate_limit_error,  # 3回目: RateLimitError
                None,  # 4回目: 成功
            ]
        )

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with (
            patch(
                "src.adapter.graphiti_episode_repository.Graphiti"
            ) as mock_client_class,
            patch("asyncio.sleep") as mock_sleep,
        ):
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
                rate_limit_max_retries=3,
                rate_limit_default_wait_time=121,
            )

            await repository.save(episode)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # 4回試行される（IndexError 1回、RateLimitError 2回、成功 1回）
        assert mock_client.add_episode.call_count == 4
        # IndexErrorで1秒 + RateLimitErrorで2秒 (1秒+1秒バッファ) × 2回 = 3回sleep
        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(1)  # IndexError: 2^0 = 1秒
        mock_sleep.assert_any_call(2)  # RateLimitError: 1秒 + 1秒バッファ

    @pytest.mark.asyncio
    async def test_save_IndexError_list_index_out_of_rangeが発生した場合_指数バックオフでリトライされること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        episode = Episode(
            name="test.pdf - chunk 0",
            body="Test content",
            source_description="Source file: test.pdf",
            reference_time=datetime(2025, 6, 13, 10, 0, 0),
            episode_type="text",
            group_id=GroupId("default"),
        )

        mock_client = AsyncMock()
        # 最初2回はIndexError、3回目は成功
        mock_client.add_episode = AsyncMock(
            side_effect=[
                IndexError("list index out of range"),
                IndexError("list index out of range"),
                None,  # 成功
            ]
        )

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with (
            patch(
                "src.adapter.graphiti_episode_repository.Graphiti"
            ) as mock_client_class,
            patch("asyncio.sleep") as mock_sleep,
        ):
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
                rate_limit_max_retries=3,
                rate_limit_default_wait_time=121,
            )

            await repository.save(episode)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # 3回試行される（2回エラー、1回成功）
        assert mock_client.add_episode.call_count == 3
        # 指数バックオフ: 1秒、2秒で2回sleep
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # 2^0 = 1秒
        mock_sleep.assert_any_call(2)  # 2^1 = 2秒

    @pytest.mark.asyncio
    async def test_save_IndexError_list_index_out_of_rangeが最大リトライ回数に達した場合_例外が再発生すること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        episode = Episode(
            name="test.pdf - chunk 0",
            body="Test content",
            source_description="Source file: test.pdf",
            reference_time=datetime(2025, 6, 13, 10, 0, 0),
            episode_type="text",
            group_id=GroupId("default"),
        )

        mock_client = AsyncMock()
        # 常にIndexErrorを発生
        mock_client.add_episode = AsyncMock(
            side_effect=IndexError("list index out of range")
        )

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with (
            patch(
                "src.adapter.graphiti_episode_repository.Graphiti"
            ) as mock_client_class,
            patch("asyncio.sleep") as mock_sleep,
        ):
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
                rate_limit_max_retries=3,
                rate_limit_default_wait_time=121,
            )

            with pytest.raises(IndexError, match="list index out of range"):
                await repository.save(episode)

        # 最大リトライ回数+1回試行される（4回）
        assert mock_client.add_episode.call_count == 4
        # 指数バックオフ: 1秒、2秒、4秒で3回sleep
        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(1)  # 2^0 = 1秒
        mock_sleep.assert_any_call(2)  # 2^1 = 2秒
        mock_sleep.assert_any_call(4)  # 2^2 = 4秒

    @pytest.mark.asyncio
    async def test_save_IndexError_他のメッセージの場合_リトライされずに例外が再発生すること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        episode = Episode(
            name="test.pdf - chunk 0",
            body="Test content",
            source_description="Source file: test.pdf",
            reference_time=datetime(2025, 6, 13, 10, 0, 0),
            episode_type="text",
            group_id=GroupId("default"),
        )

        mock_client = AsyncMock()
        # 異なるIndexErrorメッセージ
        mock_client.add_episode = AsyncMock(side_effect=IndexError("other index error"))

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with (
            patch(
                "src.adapter.graphiti_episode_repository.Graphiti"
            ) as mock_client_class,
            patch("asyncio.sleep") as mock_sleep,
        ):
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
                rate_limit_max_retries=3,
                rate_limit_default_wait_time=121,
            )

            with pytest.raises(IndexError, match="other index error"):
                await repository.save(episode)

        # リトライなしで1回のみ呼ばれる
        assert mock_client.add_episode.call_count == 1
        mock_sleep.assert_not_called()
