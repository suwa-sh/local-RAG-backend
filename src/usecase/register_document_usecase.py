"""RegisterDocumentUseCase - ドキュメント登録のユースケース"""

import logging
from dataclasses import dataclass
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.domain.group_id import GroupId
from src.adapter.filesystem_document_reader import FileSystemDocumentReader
from src.adapter.unstructured_document_parser import UnstructuredDocumentParser
from src.adapter.graphiti_episode_repository import GraphitiEpisodeRepository


@dataclass
class RegisterResult:
    """ドキュメント登録結果"""

    total_files: int
    total_chunks: int
    total_episodes: int
    success: bool
    error_message: str = ""


class RegisterDocumentUseCase:
    """ドキュメント登録のユースケース"""

    def __init__(
        self,
        file_reader: FileSystemDocumentReader,
        document_parser: UnstructuredDocumentParser,
        episode_repository: GraphitiEpisodeRepository,
    ) -> None:
        """
        RegisterDocumentUseCaseを初期化する

        Args:
            file_reader: ファイルシステムからの読み込み
            document_parser: ドキュメント解析とチャンク分割
            episode_repository: エピソード保存
        """
        self._file_reader = file_reader
        self._document_parser = document_parser
        self._episode_repository = episode_repository
        self._logger = logging.getLogger(__name__)

    async def execute(self, group_id: GroupId, directory: str) -> RegisterResult:
        """
        指定ディレクトリのドキュメントを登録する

        Args:
            group_id: グループID
            directory: 対象ディレクトリパス

        Returns:
            RegisterResult: 登録結果

        Raises:
            FileNotFoundError: ディレクトリが存在しない場合
            Exception: 登録処理でエラーが発生した場合
        """
        self._logger.info(
            f"📁 ドキュメント登録開始 - group_id: {group_id.value}, directory: {directory}"
        )

        # 1. サポート対象ファイル一覧を取得
        file_paths = self._file_reader.list_supported_files(directory)
        self._logger.info(f"📄 対象ファイル数: {len(file_paths)}")

        # 2. ドキュメントを読み込み
        documents = self._file_reader.read_documents(file_paths)
        self._logger.info(f"📖 読み込み完了ファイル数: {len(documents)}")

        if not documents:
            return RegisterResult(
                total_files=0, total_chunks=0, total_episodes=0, success=True
            )

        # 3. 各ドキュメントを処理してエピソードを作成
        all_episodes = []
        total_chunks = 0
        failed_files = []

        for i, document in enumerate(documents, 1):
            try:
                self._logger.info(
                    f"🔄 ファイル処理中 ({i}/{len(documents)}): {document.file_name}"
                )

                # ドキュメントを解析
                elements = self._document_parser.parse(document.file_path)
                self._logger.debug(f"📝 解析完了 - 要素数: {len(elements)}")

                # チャンクに分割
                chunks = self._document_parser.split_elements(elements, document)
                self._logger.debug(f"🔀 チャンク分割完了 - チャンク数: {len(chunks)}")

                # チャンクからエピソードを作成
                episodes = []
                for j, chunk in enumerate(chunks):
                    episode = chunk.to_episode(group_id)
                    episodes.append(episode)
                    self._logger.debug(
                        f"📋 エピソード作成 ({j + 1}/{len(chunks)}): {episode.name}"
                    )

                all_episodes.extend(episodes)
                total_chunks += len(chunks)

            except Exception as e:
                failed_files.append(document.file_path)
                self._logger.error(f"❌ ファイル処理失敗: {document.file_path} - {e}")
                continue

        # 4. エピソードを一括保存
        if all_episodes:
            self._logger.info(f"💾 エピソード一括保存開始 - 件数: {len(all_episodes)}")
            await self._episode_repository.save_batch(all_episodes)
            self._logger.info("✅ エピソード一括保存完了")

        return RegisterResult(
            total_files=len(documents),
            total_chunks=total_chunks,
            total_episodes=len(all_episodes),
            success=True,
        )

    def _process_single_document(
        self, document, group_id: GroupId, index: int, total: int
    ) -> Tuple[List, int, str]:
        """単一ドキュメントの処理（並列実行用）"""
        from src.adapter.logging_utils import current_file

        # 現在処理中のファイルをコンテキストに設定
        current_file.set(document.file_path)

        try:
            self._logger.info(
                f"🔄 ファイル処理中 ({index}/{total}): {document.file_name}"
            )

            # ドキュメントを解析
            elements = self._document_parser.parse(document.file_path)
            self._logger.debug(f"📝 解析完了 - 要素数: {len(elements)}")

            # チャンクに分割
            chunks = self._document_parser.split_elements(elements, document)
            self._logger.debug(f"🔀 チャンク分割完了 - チャンク数: {len(chunks)}")

            # チャンクからエピソードを作成
            episodes = []
            for j, chunk in enumerate(chunks):
                episode = chunk.to_episode(group_id)
                episodes.append(episode)
                self._logger.debug(
                    f"📋 エピソード作成 ({j + 1}/{len(chunks)}): {episode.name}"
                )

            return episodes, len(chunks), None

        except Exception as e:
            error_msg = f"❌ ファイル処理失敗: {document.file_path} - {e}"
            self._logger.error(error_msg)
            return [], 0, document.file_path

    async def execute_parallel(
        self, group_id: GroupId, directory: str, max_workers: int = 3
    ) -> RegisterResult:
        """
        ドキュメント登録の実行（並列処理版）

        Args:
            group_id: グループID
            directory: 対象ディレクトリ
            max_workers: 最大並列ワーカー数（デフォルト: 3）

        Returns:
            RegisterResult: 登録結果
        """
        self._logger.info(
            f"📁 ドキュメント登録開始（並列処理） - group_id: {group_id.value}, directory: {directory}"
        )

        # 1. ファイル一覧取得
        file_paths = self._file_reader.list_supported_files(directory)
        self._logger.info(f"📄 対象ファイル数: {len(file_paths)}")

        # 2. ファイルを読み込み
        documents = self._file_reader.read_documents(file_paths)

        self._logger.info(f"📖 読み込み完了ファイル数: {len(documents)}")

        if not documents:
            return RegisterResult(
                total_files=0, total_chunks=0, total_episodes=0, success=True
            )

        # 3. 並列処理でドキュメント処理
        all_episodes = []
        total_chunks = 0
        failed_files = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 並列実行のためのタスクを準備
            future_to_doc = {
                executor.submit(
                    self._process_single_document, doc, group_id, i, len(documents)
                ): doc
                for i, doc in enumerate(documents, 1)
            }

            # 完了したタスクから結果を取得
            for future in as_completed(future_to_doc):
                episodes, chunks, error_file = future.result()

                if error_file:
                    failed_files.append(error_file)
                else:
                    all_episodes.extend(episodes)
                    total_chunks += chunks

        # 4. エピソードを一括保存
        if all_episodes:
            self._logger.info(f"💾 エピソード一括保存開始 - 件数: {len(all_episodes)}")
            await self._episode_repository.save_batch(all_episodes)
            self._logger.info("✅ エピソード一括保存完了")

        if failed_files:
            self._logger.warning(f"⚠️ 処理失敗ファイル数: {len(failed_files)}")

        return RegisterResult(
            total_files=len(documents),
            total_chunks=total_chunks,
            total_episodes=len(all_episodes),
            success=True,
        )
