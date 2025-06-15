"""GraphitiEpisodeRepository - 高速化のためのエピソード並列保存"""

import asyncio
import logging
from typing import List, Dict
from graphiti_core.graphiti import Graphiti, EpisodeType
from graphiti_core.llm_client import OpenAIClient, LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.llm_client.errors import RateLimitError
from src.domain.episode import Episode
from src.adapter.entity_cache import get_entity_cache
from src.adapter.rate_limit_retry_handler import RateLimitRetryHandler


class GraphitiEpisodeRepository:
    """Graphitiを使用したエピソード保存リポジトリ（並列処理対応）"""

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        llm_api_key: str,
        llm_base_url: str,
        llm_model: str,
        rerank_model: str,
        embedding_api_key: str,
        embedding_base_url: str,
        embedding_model: str,
        rate_limit_max_retries: int = 3,
        rate_limit_default_wait_time: int = 121,
    ) -> None:
        """
        GraphitiEpisodeRepositoryを初期化する

        Args:
            neo4j_uri: Neo4jのURI
            neo4j_user: Neo4jのユーザー名
            neo4j_password: Neo4jのパスワード
            llm_api_key: LLM APIキー
            llm_base_url: LLM APIのベースURL
            llm_model: 使用するLLMモデル
            rerank_model: 使用するrerankモデル（small_model用）
            embedding_api_key: 埋め込みAPIキー
            embedding_base_url: 埋め込みAPIのベースURL
            embedding_model: 使用する埋め込みモデル
        """
        # LLMクライアントの設定
        llm_config = LLMConfig(
            api_key=llm_api_key,
            base_url=llm_base_url,
            model=llm_model,
            small_model=rerank_model,
        )
        llm_client = OpenAIClient(config=llm_config)

        # 埋め込みクライアントの設定
        embedder_config = OpenAIEmbedderConfig(
            api_key=embedding_api_key,
            base_url=embedding_base_url,
            embedding_model=embedding_model,
        )
        embedder = OpenAIEmbedder(config=embedder_config)

        # Graphitiクライアントの初期化
        self.client = Graphiti(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
            llm_client=llm_client,
            embedder=embedder,
        )

        # ロガーの初期化
        self._logger = logging.getLogger(__name__)

        # エンティティキャッシュの初期化
        self.entity_cache = get_entity_cache()

        # Rate limitリトライハンドラーの初期化
        self.retry_handler = RateLimitRetryHandler(
            max_retries=rate_limit_max_retries,
            default_wait_time=rate_limit_default_wait_time,
            logger=self._logger,
        )

        self._logger.info(f"🔗 Graphitiクライアント初期化完了 - Neo4j: {neo4j_uri}")
        self._logger.info("📋 エンティティキャッシュ初期化完了")

    async def save(self, episode: Episode) -> None:
        """
        単一のエピソードを保存する

        Args:
            episode: 保存するエピソード

        Raises:
            Exception: Graphitiでエラーが発生した場合
        """
        # episode_typeを対応するEpisodeTypeに変換
        episode_type_mapping = {
            "text": EpisodeType.text,
            "json": EpisodeType.json,
            "message": EpisodeType.message,
        }

        source_type = episode_type_mapping.get(episode.episode_type, EpisodeType.text)

        self._logger.debug(f"💾 エピソード保存開始: {episode.name}")
        self._logger.debug(f"  - group_id: {episode.group_id.value}")
        self._logger.debug(f"  - episode_type: {episode.episode_type} -> {source_type}")
        self._logger.debug(f"  - body_length: {len(episode.body)}")

        # Rate limitリトライ処理
        attempt = 0
        while attempt <= self.retry_handler.max_retries:
            try:
                await self.client.add_episode(
                    name=episode.name,
                    episode_body=episode.body,
                    source_description=episode.source_description,
                    reference_time=episode.reference_time,
                    source=source_type,
                    group_id=episode.group_id.value,
                )
                self._logger.debug(f"✅ エピソード保存完了: {episode.name}")
                return
            except RateLimitError as e:
                if attempt < self.retry_handler.max_retries:
                    retry_after = self.retry_handler.extract_retry_after_time(e)
                    if retry_after:
                        self._logger.info(
                            f"🔄 Rate limit detected. Waiting {retry_after} seconds before retry "
                            f"(attempt {attempt + 1}/{self.retry_handler.max_retries})"
                        )
                        await asyncio.sleep(retry_after)
                    else:
                        self._logger.info(
                            f"🔄 Rate limit detected. Using default wait time "
                            f"({self.retry_handler.default_wait_time} seconds) before retry "
                            f"(attempt {attempt + 1}/{self.retry_handler.max_retries})"
                        )
                        await asyncio.sleep(self.retry_handler.default_wait_time)
                    attempt += 1
                else:
                    self._logger.error(
                        f"❌ Rate limit error after {self.retry_handler.max_retries} retries: {episode.name}"
                    )
                    raise
            except Exception as e:
                self._logger.error(f"❌ エピソード保存失敗: {episode.name} - {e}")
                raise

    async def save_batch(
        self, episodes: List[Episode], max_concurrent: int = 3
    ) -> None:
        """
        複数のエピソードを並列で一括保存する

        Args:
            episodes: 保存するエピソードのリスト
            max_concurrent: 最大同時実行数（デフォルト: 3）

        Raises:
            Exception: Graphitiでエラーが発生した場合
        """
        if not episodes:
            self._logger.warning("⚠️ 保存対象のエピソードがありません")
            return

        self._logger.info(f"📦 一括保存開始（並列）: {len(episodes)}件のエピソード")

        # ファイルごとにエピソードをグループ化
        episodes_by_file = self._group_episodes_by_file(episodes)

        # セマフォで同時実行数を制限
        semaphore = asyncio.Semaphore(max_concurrent)

        async def save_with_semaphore(
            episode: Episode, file_path: str, index: int, total: int
        ):
            async with semaphore:
                # ファイルコンテキストを設定
                from src.adapter.logging_utils import current_file

                current_file.set(file_path)

                self._logger.debug(
                    f"📝 エピソード保存中 ({index}/{total}): {episode.name}"
                )
                await self.save(episode)

        # 全エピソードの保存タスクを作成
        tasks = []
        total_episodes = len(episodes)
        current_index = 0

        for file_path, file_episodes in episodes_by_file.items():
            self._logger.info(
                f"📁 ファイル処理開始: {file_path} ({len(file_episodes)}エピソード)"
            )

            for episode in file_episodes:
                current_index += 1
                task = save_with_semaphore(
                    episode, file_path, current_index, total_episodes
                )
                tasks.append(task)

        # 全タスクを並列実行
        await asyncio.gather(*tasks)

        # キャッシュ統計をログ出力
        self.entity_cache.log_cache_stats()
        self._logger.info(f"✅ 一括保存完了（並列）: {len(episodes)}件のエピソード")

    def _group_episodes_by_file(
        self, episodes: List[Episode]
    ) -> Dict[str, List[Episode]]:
        """
        エピソードをファイルごとにグループ化する

        Args:
            episodes: エピソードのリスト

        Returns:
            Dict[str, List[Episode]]: ファイルパスをキーとしたエピソードのグループ
        """
        episodes_by_file = {}

        for episode in episodes:
            file_path = self._extract_file_path_from_source(episode.source_description)

            if file_path not in episodes_by_file:
                episodes_by_file[file_path] = []
            episodes_by_file[file_path].append(episode)

        return episodes_by_file

    def _extract_file_path_from_source(self, source_description: str) -> str:
        """
        source_descriptionからファイルパスを抽出する

        Args:
            source_description: ソース説明文字列

        Returns:
            str: 抽出されたファイルパス
        """
        # "Source file: /path/to/file.ext" の形式からパスを抽出
        if source_description.startswith("Source file: "):
            return source_description[13:]  # "Source file: " の文字数分をスキップ
        else:
            # フォールバック: 説明文字列全体を使用
            return source_description

    async def close(self) -> None:
        """
        Graphitiクライアントを閉じる
        """
        await self.client.close()
