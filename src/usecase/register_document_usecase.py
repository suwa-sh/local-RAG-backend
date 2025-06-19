"""RegisterDocumentUseCase - ドキュメント登録のユースケース"""

import logging
import multiprocessing
import time
from collections import Counter
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

    def _determine_optimal_workers(
        self, documents: List, requested_workers: int
    ) -> int:
        """
        ファイルタイプに応じて最適なワーカー数を決定する

        Args:
            documents: 処理対象のドキュメントリスト
            requested_workers: リクエストされたワーカー数

        Returns:
            int: 最適化されたワーカー数
        """
        if not documents:
            return 1

        # ファイルタイプの統計を取得
        file_types = [doc.file_type for doc in documents]
        type_counter = Counter(file_types)
        total_files = len(documents)

        # 画像ファイルのタイプ（CPU負荷が高い）
        image_types = {"png", "jpg", "jpeg", "bmp", "tiff", "tif", "heic"}
        image_count = sum(
            count
            for file_type, count in type_counter.items()
            if file_type.lower() in image_types
        )

        # PDF ファイルの数（メモリ使用量が多い）
        pdf_count = type_counter.get("pdf", 0)

        # 画像ファイルの割合
        image_ratio = image_count / total_files
        pdf_ratio = pdf_count / total_files

        cpu_count = multiprocessing.cpu_count()

        # 最適なワーカー数を決定
        if image_ratio > 0.5:  # 画像ファイルが50%以上
            optimal_workers = min(cpu_count // 2, total_files, 4)
            self._logger.info(
                f"📊 ワーカー数調整 - 画像ファイル率 {image_ratio:.1%}: "
                f"{requested_workers} → {optimal_workers} ワーカー"
            )
        elif pdf_ratio > 0.7:  # PDFファイルが70%以上
            optimal_workers = min(cpu_count // 2, total_files, 6)
            self._logger.info(
                f"📊 ワーカー数調整 - PDF率 {pdf_ratio:.1%}: "
                f"{requested_workers} → {optimal_workers} ワーカー"
            )
        else:  # テキストファイルが多い場合は積極的に並列化
            optimal_workers = min(cpu_count, total_files, requested_workers)
            if optimal_workers != requested_workers:
                self._logger.info(
                    f"📊 ワーカー数調整 - 軽量ファイル中心: "
                    f"{requested_workers} → {optimal_workers} ワーカー"
                )

        # ファイル種別の統計をログ出力
        self._logger.info(
            f"📈 ファイル統計 - 総数: {total_files}, 画像: {image_count}, "
            f"PDF: {pdf_count}, その他: {total_files - image_count - pdf_count}"
        )

        return max(1, optimal_workers)  # 最低1ワーカーは確保

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

            # 全体の処理時間計測開始
            start_time = time.time()

            # ドキュメントを解析
            parse_start = time.time()
            elements = self._document_parser.parse(document.file_path)
            parse_time = time.time() - parse_start
            self._logger.debug(f"📝 解析完了 - 要素数: {len(elements)}")

            # チャンクに分割
            chunk_start = time.time()
            chunks = self._document_parser.split_elements(elements, document)
            chunk_time = time.time() - chunk_start
            self._logger.debug(f"🔀 チャンク分割完了 - チャンク数: {len(chunks)}")

            # チャンクからエピソードを作成
            episode_start = time.time()
            episodes = []
            for j, chunk in enumerate(chunks):
                episode = chunk.to_episode(group_id)
                episodes.append(episode)
                self._logger.debug(
                    f"📋 エピソード作成 ({j + 1}/{len(chunks)}): {episode.name}"
                )
            episode_time = time.time() - episode_start

            # 全体の処理時間
            total_time = time.time() - start_time

            # パフォーマンス情報をログ出力
            self._logger.info(
                f"⏱️ パフォーマンス - {document.file_name} ({document.file_type}): "
                f"解析 {parse_time:.2f}秒, チャンク分割 {chunk_time:.2f}秒, "
                f"エピソード作成 {episode_time:.2f}秒, 合計 {total_time:.2f}秒"
            )

            return episodes, len(chunks), None

        except Exception as e:
            error_msg = f"❌ ファイル処理失敗: {document.file_path} - {e}"
            self._logger.error(error_msg)
            return [], 0, document.file_path

    async def execute_parallel(
        self,
        group_id: GroupId,
        directory: str,
        max_workers: int = 3,
        register_workers: int = 2,
    ) -> RegisterResult:
        """
        ドキュメント登録の実行（2段階並列処理版）

        Args:
            group_id: グループID
            directory: 対象ディレクトリ
            max_workers: チャンク処理の最大並列ワーカー数（デフォルト: 3）
            register_workers: 登録処理の最大並列ワーカー数（デフォルト: 2）

        Returns:
            RegisterResult: 登録結果
        """
        # インフラ初期化（ビジネスロジック実行の前提条件）
        self._logger.info("🏗️ Graphitiインデックス構築中...")
        await self._episode_repository.initialize()

        self._logger.info(
            f"📁 ドキュメント登録開始（2段階並列処理） - group_id: {group_id.value}, directory: {directory}"
        )
        self._logger.info(
            f"⚙️ 並列処理設定 - チャンク処理: {max_workers}ワーカー, 登録処理: {register_workers}ワーカー"
        )

        # 1. ファイル一覧取得
        file_paths = self._file_reader.list_supported_files(directory)
        self._logger.info(f"📄 対象ファイル数: {len(file_paths)}")

        # 2. ファイルを読み込み（基準ディレクトリを指定して相対パス計算）
        documents = self._file_reader.read_documents(file_paths, directory)

        self._logger.info(f"📖 読み込み完了ファイル数: {len(documents)}")

        if not documents:
            return RegisterResult(
                total_files=0, total_chunks=0, total_episodes=0, success=True
            )

        # 3. 最適なワーカー数を決定
        optimal_workers = self._determine_optimal_workers(documents, max_workers)

        # 4. 並列処理でドキュメント処理
        all_episodes = []
        total_chunks = 0
        failed_files = []

        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
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

        # 5. エピソードを一括保存（登録用ワーカー数で制御）
        if all_episodes:
            self._logger.info(
                f"💾 エピソード一括保存開始 - 件数: {len(all_episodes)}, 登録ワーカー: {register_workers}"
            )
            save_start = time.time()
            await self._episode_repository.save_batch(
                all_episodes, max_concurrent=register_workers
            )
            save_time = time.time() - save_start
            self._logger.info(
                f"✅ エピソード一括保存完了 - 保存時間: {save_time:.2f}秒, 登録ワーカー: {register_workers}"
            )

        if failed_files:
            self._logger.warning(f"⚠️ 処理失敗ファイル数: {len(failed_files)}")

        return RegisterResult(
            total_files=len(documents),
            total_chunks=total_chunks,
            total_episodes=len(all_episodes),
            success=True,
        )
