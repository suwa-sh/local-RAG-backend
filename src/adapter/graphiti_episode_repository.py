"""GraphitiEpisodeRepository - 高速化のためのエピソード並列保存"""

import asyncio
import logging
import threading
from typing import List, Dict
from graphiti_core.graphiti import Graphiti, EpisodeType
from graphiti_core.llm_client import OpenAIClient, LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.llm_client.errors import RateLimitError
from src.domain.episode import Episode
from src.adapter.entity_cache import get_entity_cache
from src.adapter.rate_limit_retry_handler import RateLimitRetryHandler
from src.adapter.rate_limit_coordinator import get_rate_limit_coordinator


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
            logger=self._logger,
        )

        # Rate limitコーディネーターの初期化
        self.rate_limit_coordinator = get_rate_limit_coordinator()

        self._logger.info(f"🔗 Graphitiクライアント初期化完了 - Neo4j: {neo4j_uri}")
        self._logger.info("📋 エンティティキャッシュ初期化完了")
        self._logger.info("🔄 Rate Limitスレッド同期コーディネーター初期化完了")

    async def initialize(self) -> None:
        """
        Graphitiクライアントの非同期初期化
        インデックスと制約を構築する
        """
        try:
            await self.client.build_indices_and_constraints()
            self._logger.info("🏗️ Graphiti インデックスと制約の構築完了")
        except Exception as e:
            self._logger.error(f"❌ Graphiti インデックス構築エラー: {e}")
            raise

    async def save(self, episode: Episode) -> None:
        """
        単一のエピソードを保存する

        Args:
            episode: 保存するエピソード

        Raises:
            Exception: Graphitiでエラーが発生した場合
        """
        # スレッドIDを取得
        thread_id = str(threading.current_thread().ident or "unknown")

        # Rate Limit状態をチェックし、必要に応じて待機
        await self.rate_limit_coordinator.check_and_wait_if_needed(thread_id)

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

        # エラー別のリトライカウンター
        rate_limit_attempts = 0
        index_error_attempts = 0

        while True:
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
                if rate_limit_attempts < self.retry_handler.max_retries:
                    retry_after = self.retry_handler.extract_retry_after_time(e)
                    wait_time = (
                        retry_after
                        if retry_after
                        else self.retry_handler.default_wait_time
                    )

                    # Rate Limitを全スレッドに通知
                    await self.rate_limit_coordinator.notify_rate_limit(
                        thread_id, wait_time, str(e)
                    )

                    # このスレッドが実際に待機
                    await self.rate_limit_coordinator.wait_for_rate_limit_completion(
                        thread_id
                    )

                    rate_limit_attempts += 1
                else:
                    self._logger.error(
                        f"❌ Rate limit error after {self.retry_handler.max_retries} retries: {episode.name}"
                    )
                    raise
            except IndexError as e:
                if "list index out of range" in str(e):
                    if index_error_attempts < self.retry_handler.max_retries:
                        # 指数バックオフ（1秒、2秒、4秒...）- graphitiエンティティ競合エラー用
                        wait_time = 2**index_error_attempts
                        self._logger.warning(
                            f"⚠️ Graphitiエンティティ競合エラー。{wait_time}秒後にリトライ "
                            f"(index error attempt {index_error_attempts + 1}/{self.retry_handler.max_retries}): {episode.name}"
                        )
                        await asyncio.sleep(wait_time)
                        index_error_attempts += 1
                    else:
                        self._logger.error(
                            f"❌ エンティティ競合エラー（最大リトライ回数超過）: {episode.name}"
                        )
                        raise
                else:
                    self._logger.error(f"❌ IndexError（非競合）: {episode.name} - {e}")
                    raise
            except Exception as e:
                self._logger.error(f"❌ エピソード保存失敗: {episode.name} - {e}")
                raise
