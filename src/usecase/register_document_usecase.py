"""RegisterDocumentUseCase - ドキュメント登録のユースケース"""

import logging
import multiprocessing
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Any, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.domain.group_id import GroupId
from src.adapter.filesystem_document_reader import FileSystemDocumentReader
from src.adapter.unstructured_document_parser import UnstructuredDocumentParser
from src.adapter.graphiti_episode_repository import GraphitiEpisodeRepository
from src.adapter.chunk_file_manager import ChunkFileManager
from src.main.settings import load_config


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
        chunk_file_manager: ChunkFileManager | None = None,
    ) -> None:
        """
        RegisterDocumentUseCaseを初期化する

        Args:
            file_reader: ファイルシステムからの読み込み
            document_parser: ドキュメント解析とチャンク分割
            episode_repository: エピソード保存
            chunk_file_manager: チャンクファイル管理（Noneの場合は自動生成）
        """
        self._file_reader = file_reader
        self._document_parser = document_parser
        self._episode_repository = episode_repository
        self._chunk_file_manager = chunk_file_manager or ChunkFileManager()
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

    def _process_single_document_with_recovery(
        self,
        document,
        group_id: GroupId,
        index: int,
        total: int,
        base_directory: str = None,
    ) -> Tuple[List, int, str]:
        """
        単一ドキュメントの統一処理フロー（エラー再処理対応）

        Args:
            document: ドキュメント
            group_id: グループID
            index: ドキュメントのインデックス
            total: 総ドキュメント数
            base_directory: 基準ディレクトリ（ファイル移動用）

        Returns:
            Tuple[List, int, str]: (エピソードリスト, チャンク数, エラーファイルパス)
        """
        from src.adapter.logging_utils import current_file

        # 現在処理中のファイルをコンテキストに設定
        current_file.set(document.file_path)

        try:
            self._logger.info(
                f"🔄 ファイル処理中 ({index}/{total}): {document.file_name}"
            )

            # 全体の処理時間計測開始
            start_time = time.time()

            # ステップ1: チャンクファイルの存在確認
            chunks = []
            if self._chunk_file_manager.has_chunk_files(document.file_path):
                # 保存されたチャンクを読み込み
                self._logger.info(f"📁 保存済みチャンク読み込み: {document.file_name}")
                chunks, metadata = self._chunk_file_manager.load_chunks(
                    document.file_path
                )

                # 最後に処理された位置を取得
                last_processed = metadata.get("last_processed_position", -1)

                # 未処理のチャンクのみを対象とする
                if last_processed >= 0:
                    chunks = chunks[last_processed + 1 :]
                    self._logger.info(
                        f"🔄 再処理開始: 位置 {last_processed + 1} から {len(chunks)}チャンク"
                    )

            else:
                # 新規処理: 元ファイルからチャンク生成
                self._logger.debug(f"🆕 新規処理: {document.file_name}")

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

                # パフォーマンス情報をログ出力
                self._logger.info(
                    f"⏱️ パフォーマンス - {document.file_name} ({document.file_type}): "
                    f"解析 {parse_time:.2f}秒, チャンク分割 {chunk_time:.2f}秒"
                )

            # ステップ2: チャンクの順次登録
            episodes = []
            total_chunks = len(chunks)

            if total_chunks == 0:
                self._logger.warning(f"⚠️ 処理対象チャンクなし: {document.file_name}")
                # チャンクファイルが存在する場合は削除
                if self._chunk_file_manager.has_chunk_files(document.file_path):
                    self._chunk_file_manager.delete_all_chunks(document.file_path)
                return [], 0, None

            for i, chunk in enumerate(chunks):
                try:
                    # エピソードを作成
                    episode = chunk.to_episode(group_id)
                    episodes.append(episode)

                    self._logger.debug(
                        f"📋 エピソード作成完了 ({i + 1}/{total_chunks}): {episode.name}"
                    )

                except Exception as e:
                    # エラー発生時: 残りのチャンクを保存
                    remaining_chunks = chunks[i:]
                    last_processed_position = i - 1 if i > 0 else -1

                    self._logger.error(
                        f"❌ チャンク処理エラー (位置: {i}): {document.file_name} - {e}"
                    )

                    # 残りチャンクを保存
                    self._chunk_file_manager.save_chunks(
                        remaining_chunks,
                        document.file_path,
                        last_processed_position,
                        str(e),
                    )

                    return episodes, len(episodes), document.file_path

            # ステップ3: 全成功時の処理
            total_time = time.time() - start_time
            self._logger.info(
                f"✅ ファイル処理完了: {document.file_name} "
                f"({total_chunks}チャンク, {total_time:.2f}秒)"
            )

            # チャンクファイルが存在する場合は削除（処理完了のため）
            if self._chunk_file_manager.has_chunk_files(document.file_path):
                self._chunk_file_manager.delete_all_chunks(document.file_path)

            # エピソードが生成されている場合、エピソードファイルを保存してwork/に移動
            if episodes and base_directory and "/input" in document.file_path:
                try:
                    # エピソードファイル保存
                    self._chunk_file_manager.save_episodes(document.file_path, episodes)

                    # ファイル移動 (input → work)
                    work_directory = base_directory.replace("/input", "/work")
                    new_path = self._file_reader.move_file(
                        document.file_path, work_directory
                    )

                    # ドキュメントのパスを更新
                    document.file_path = new_path

                    self._logger.info(
                        f"📁 処理中ファイル移動: {document.file_name} → work/"
                    )
                except Exception as e:
                    self._logger.error(
                        f"❌ ファイル移動失敗: {document.file_name} - {e}"
                    )
                    # 移動に失敗してもエピソードは返す

            return episodes, total_chunks, None

        except Exception as e:
            error_msg = f"❌ ファイル処理失敗: {document.file_path} - {e}"
            self._logger.error(error_msg)
            return [], 0, document.file_path

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

        # 1. ファイル一覧取得（input/とwork/の両方から）
        input_directory = directory if "/input" in directory else f"{directory}/input"
        work_directory = (
            directory.replace("/input", "/work")
            if "/input" in directory
            else f"{directory}/work"
        )

        # input/ディレクトリのファイル
        input_files = []
        if Path(input_directory).exists():
            input_files = self._file_reader.list_supported_files(input_directory)

        # work/ディレクトリのファイル
        work_files = []
        if Path(work_directory).exists():
            work_files = self._file_reader.list_supported_files(work_directory)

        file_paths = input_files + work_files
        self._logger.info(
            f"📄 対象ファイル数: {len(file_paths)} (input: {len(input_files)}, work: {len(work_files)})"
        )

        # 2. ファイル移動のための基準ディレクトリを設定
        self._file_reader._base_directory = directory

        # 3. ファイルを読み込み（基準ディレクトリを指定して相対パス計算）
        documents = self._file_reader.read_documents(file_paths, directory)

        self._logger.info(f"📖 読み込み完了ファイル数: {len(documents)}")

        if not documents:
            return RegisterResult(
                total_files=0, total_chunks=0, total_episodes=0, success=True
            )

        # 3. 最適なワーカー数を決定
        optimal_workers = self._determine_optimal_workers(documents, max_workers)

        # 4. 並列処理でドキュメント処理（エラー再処理対応）
        all_episodes = []
        total_chunks = 0
        failed_files = []

        # ファイルの場所に応じて処理方法を決定
        documents_to_process = []
        documents_in_work = []

        for doc in documents:
            # work/ディレクトリのファイルは既にエピソードファイルが存在するはず
            if "/work/" in doc.file_path:
                # work/ディレクトリのファイルは既にエピソード化済み
                if self._chunk_file_manager.has_saved_episodes(doc.file_path):
                    documents_in_work.append(doc)
                    self._logger.info(f"🔄 処理中ファイル発見: {doc.file_name} (work/)")
                else:
                    # エピソードファイルがない場合は通常処理に戻す
                    documents_to_process.append(doc)
                    self._logger.warning(
                        f"⚠️ エピソードファイルなし: {doc.file_name} (work/) - 再処理します"
                    )
            else:
                # 通常の処理対象
                documents_to_process.append(doc)

        # 通常のドキュメント処理（チャンク生成から開始）
        if documents_to_process:
            with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
                # 並列実行のためのタスクを準備（統一処理フロー使用）
                future_to_doc = {
                    executor.submit(
                        self._process_single_document_with_recovery,
                        doc,
                        group_id,
                        i,
                        len(documents_to_process),
                        directory,  # 基準ディレクトリを渡す
                    ): doc
                    for i, doc in enumerate(documents_to_process, 1)
                }

                # 完了したタスクから結果を取得
                for future in as_completed(future_to_doc):
                    episodes, chunks, error_file = future.result()

                    if error_file:
                        failed_files.append(error_file)
                    else:
                        all_episodes.extend(episodes)
                        total_chunks += chunks

        # 5. 設定読み込み
        config = load_config()
        batch_size = config.parallel.episode_batch_size

        # work/ディレクトリのファイルからエピソードを読み込む
        if documents_in_work:
            self._logger.info(
                f"📁 work/ディレクトリのファイル処理: {len(documents_in_work)}ファイル"
            )

            # work/ディレクトリのファイルはエピソードを読み込むだけ
            work_episodes_by_file = {}
            for doc in documents_in_work:
                try:
                    # エピソードファイルを読み込み
                    episodes = self._chunk_file_manager.load_episodes(doc.file_path)
                    if episodes:
                        work_episodes_by_file[doc.file_path] = episodes
                        self._logger.info(
                            f"📁 エピソード読み込み完了: {doc.file_name} ({len(episodes)}エピソード)"
                        )
                except Exception as e:
                    self._logger.error(
                        f"❌ エピソードファイル読み込み失敗: {doc.file_path} - {e}"
                    )
                    failed_files.append(doc.file_path)

            # work/ディレクトリのエピソードも保存対象に追加
            if work_episodes_by_file:
                # 既存の処理と統合するため、documents_to_processに追加
                # （エピソードは既に work_episodes_by_file に保存されている）
                await self._save_work_episodes_with_progress(
                    work_episodes_by_file, batch_size, register_workers
                )

        # 全エピソードの分割保存（進捗追跡付き）
        if all_episodes:
            self._logger.info(
                f"💾 エピソード分割保存開始 - 件数: {len(all_episodes)}, "
                f"バッチサイズ: {batch_size}, 登録ワーカー: {register_workers}"
            )
            save_start = time.time()

            try:
                await self._save_episodes_with_progress_tracking(
                    all_episodes, documents_to_process, batch_size, register_workers
                )
                save_time = time.time() - save_start
                self._logger.info(
                    f"✅ エピソード分割保存完了 - 保存時間: {save_time:.2f}秒"
                )
            except Exception as e:
                save_time = time.time() - save_start
                self._logger.error(
                    f"❌ エピソード分割保存失敗 - 保存時間: {save_time:.2f}秒, エラー: {e}"
                )
                # エラーでも処理を継続（部分保存されたエピソードは進捗に記録済み）

        # 6. 処理完了ファイルをdoneディレクトリに移動
        # 注: 新方式ではwork→doneの移動はエピソード登録時に個別に実行されるため、
        # ここでは互換性のため残存ファイルのチェックのみ行う
        done_directory = (
            directory.replace("/input", "/done")
            if "/input" in directory
            else f"{directory}/done"
        )
        successful_files = []

        # すべてのドキュメントをチェック（互換性のため）
        all_processed_documents = documents_to_process

        for doc in all_processed_documents:
            if doc.file_path not in failed_files:
                try:
                    # 既にdone/に移動済みかチェック
                    if "/done/" in doc.file_path:
                        successful_files.append(doc.file_path)
                        continue

                    # チャンクファイルと残存エピソードファイルが残っていないことを確認
                    has_chunks = self._chunk_file_manager.has_chunk_files(doc.file_path)
                    has_remaining_episodes = (
                        self._chunk_file_manager.has_saved_episodes(doc.file_path)
                    )

                    if not has_chunks and not has_remaining_episodes:
                        # 古い方式の互換性のため、input/のファイルはdone/に移動
                        if "/input/" in doc.file_path:
                            moved_path = self._file_reader.move_file(
                                doc.file_path, done_directory
                            )
                            successful_files.append(moved_path)
                            self._logger.info(
                                f"📁 完了ファイル移動: {doc.file_name} → done/"
                            )
                        else:
                            successful_files.append(doc.file_path)
                    else:
                        skip_reasons = []
                        if has_chunks:
                            skip_reasons.append("チャンクファイル残存")
                        if has_remaining_episodes:
                            skip_reasons.append("未処理エピソード残存")

                        self._logger.debug(
                            f"⚠️ ファイル移動スキップ: {doc.file_name} ({', '.join(skip_reasons)})"
                        )
                except Exception as e:
                    self._logger.warning(
                        f"⚠️ ファイル移動確認失敗: {doc.file_name} - {e}"
                    )

        if failed_files:
            self._logger.warning(f"⚠️ 処理失敗ファイル数: {len(failed_files)}")
            for failed_file in failed_files:
                self._logger.warning(f"  - {failed_file}")

        if successful_files:
            self._logger.info(f"✅ 完了ファイル移動数: {len(successful_files)}")

        # エラー再処理の統計情報を出力
        cache_stats = self._chunk_file_manager.get_cache_stats()
        if cache_stats["total_cached_files"] > 0:
            self._logger.info(
                f"📊 チャンクキャッシュ: {cache_stats['total_cached_files']}ファイル, "
                f"{cache_stats['total_chunks']}チャンク, {cache_stats['total_size_mb']}MB"
            )

        return RegisterResult(
            total_files=len(all_processed_documents),
            total_chunks=total_chunks,
            total_episodes=len(all_episodes),
            success=len(failed_files) == 0,  # 失敗ファイルがない場合のみ成功
            error_message=f"{len(failed_files)}個のファイルで処理に失敗しました"
            if failed_files
            else "",
        )

    async def _save_episodes_with_progress_tracking(
        self,
        all_episodes: List,
        documents: List,
        batch_size: int,
        max_concurrent: int,
    ) -> None:
        """
        エピソードを分割保存し、進捗を追跡する

        Args:
            all_episodes: 保存するエピソードのリスト
            documents: ドキュメントのリスト
            batch_size: バッチサイズ
            max_concurrent: 最大同時実行数

        Raises:
            Exception: 保存に失敗した場合
        """
        # エピソードをファイル別にグループ化
        episodes_by_file = {}
        for episode in all_episodes:
            # エピソード名からファイルパスを抽出（仮の実装）
            source_file = self._extract_source_file_from_episode(episode, documents)
            if source_file not in episodes_by_file:
                episodes_by_file[source_file] = []
            episodes_by_file[source_file].append(episode)

        # ファイルごとに分割保存を実行
        for file_path, file_episodes in episodes_by_file.items():
            await self._save_file_episodes_with_progress(
                file_path, file_episodes, batch_size, max_concurrent
            )

    async def _save_file_episodes_with_progress(
        self,
        file_path: str,
        file_episodes: List,
        batch_size: int,  # 互換性のため保持（エピソード単位保存では未使用）
        max_concurrent: int,
    ) -> None:
        """
        単一ファイルのエピソードをエピソード単位で保存し、進捗を追跡する（事前ファイル保存方式）

        Args:
            file_path: ファイルパス
            file_episodes: ファイルのエピソードリスト
            batch_size: バッチサイズ（互換性のため保持、エピソード単位保存では未使用）
            max_concurrent: 最大同時実行数

        Raises:
            Exception: 保存に失敗した場合
        """
        # batch_sizeは互換性のため保持しているが、エピソード単位保存では使用しない
        _ = batch_size
        total_episodes = len(file_episodes)

        # 事前に全エピソードをファイル保存する（Stage 1: 事前保存）
        if not self._chunk_file_manager.has_saved_episodes(file_path):
            self._logger.info(
                f"💾 事前エピソード保存開始: {file_path} ({total_episodes}エピソード)"
            )
            self._chunk_file_manager.save_episodes(file_path, file_episodes, 0)

            self._logger.info(f"✅ 事前エピソード保存完了: {file_path}")

        # エピソードファイルから残存分を確認
        start_index = 0

        # 残存エピソードファイルから未処理分を特定
        remaining_episodes = []
        for episode_index in range(start_index, total_episodes):
            episode_file = self._chunk_file_manager._get_episode_file_path(
                file_path, episode_index
            )
            if episode_file.exists():
                try:
                    # ファイルからエピソードを読み込み
                    episode_list = self._chunk_file_manager.load_episodes(
                        file_path, episode_index, episode_index
                    )
                    if episode_list:
                        remaining_episodes.append((episode_index, episode_list[0]))
                except Exception as e:
                    self._logger.warning(
                        f"⚠️ エピソードファイル読み込み失敗: {episode_file} - {e}"
                    )

        if not remaining_episodes:
            self._logger.info(f"✅ エピソード保存済み: {file_path}")
            return

        self._logger.info(
            f"🔄 エピソード並列保存開始: {file_path} "
            f"({len(remaining_episodes)}/{total_episodes}エピソード残り)"
        )

        # Stage 2: エピソード単位での並列保存
        await self._save_episodes_parallel_with_progress(
            file_path, remaining_episodes, max_concurrent, total_episodes
        )

        # 全保存完了時
        self._logger.info(
            f"✅ ファイルエピソード保存完了: {file_path} ({total_episodes}エピソード)"
        )

    async def _save_episodes_parallel_with_progress(
        self,
        file_path: str,
        remaining_episodes: List[Tuple[int, Any]],
        max_concurrent: int,
        total_episodes: int,
    ) -> None:
        """
        エピソードを並列で保存し、進捗を追跡する

        Args:
            file_path: ファイルパス
            remaining_episodes: 残存エピソードのリスト（インデックス、エピソード）のタプル
            max_concurrent: 最大同時実行数
            total_episodes: 総エピソード数

        Raises:
            Exception: 保存に失敗した場合
        """
        import asyncio

        # セマフォで同時実行数を制限
        semaphore = asyncio.Semaphore(max_concurrent)

        async def save_single_with_semaphore(episode_index: int, episode):
            async with semaphore:
                await self._save_single_episode_with_progress(
                    file_path, episode_index, episode, total_episodes
                )

        # 全エピソードの保存タスクを作成
        tasks = []
        for episode_index, episode in remaining_episodes:
            task = save_single_with_semaphore(episode_index, episode)
            tasks.append(task)

        # 並列実行（例外が発生しても他のタスクを継続）
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 結果を確認し、エラーがあればログ出力
        error_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                episode_index, episode = remaining_episodes[i]
                self._logger.error(
                    f"❌ エピソード保存失敗: {file_path} [index:{episode_index}] {episode.name} - {result}"
                )
                error_count += 1

        if error_count > 0:
            self._logger.warning(
                f"⚠️ エピソード保存で{error_count}件のエラーが発生: {file_path}"
            )
        else:
            self._logger.info(f"✅ 全エピソード保存成功: {file_path}")

    async def _save_single_episode_with_progress(
        self,
        file_path: str,
        episode_index: int,
        episode: Any,
        total_episodes: int,
    ) -> None:
        """
        単一エピソードを保存し、成功時にファイルを削除して進捗を更新する

        Args:
            file_path: ファイルパス
            episode_index: エピソードのインデックス
            episode: エピソード
            total_episodes: 総エピソード数

        Raises:
            Exception: 保存に失敗した場合
        """
        # ファイルコンテキストを設定
        from src.adapter.logging_utils import current_file

        current_file.set(file_path)

        self._logger.debug(
            f"📝 エピソード保存中 [{episode_index}/{total_episodes - 1}]: {episode.name}"
        )

        # エピソードを保存（ここで例外が発生する可能性がある）
        await self._episode_repository.save(episode)

        # ここまで到達 = 保存成功
        # 成功時: 対応するエピソードファイルを即座に削除
        self._chunk_file_manager.delete_episode_files(
            file_path, episode_index, episode_index
        )

        self._logger.debug(f"✅ エピソード保存成功 [{episode_index}]: {episode.name}")

        # 全エピソード処理完了チェック（work→done移動）
        if not self._chunk_file_manager.has_saved_episodes(file_path):
            # work/ディレクトリのファイルのみ移動対象
            if "/work/" in file_path:
                done_directory = file_path.replace("/work/", "/done/")
                # ディレクトリ部分のみ抽出
                done_dir = str(Path(done_directory).parent)

                try:
                    self._file_reader.move_file(file_path, done_dir)
                    self._logger.info(
                        f"📁 完了ファイル移動: {Path(file_path).name} → done/"
                    )
                except FileNotFoundError:
                    # 既に他のスレッドが移動済み
                    self._logger.debug(
                        f"📁 ファイル既に移動済み: {Path(file_path).name}"
                    )
                except Exception as e:
                    self._logger.warning(
                        f"⚠️ ファイル移動失敗: {Path(file_path).name} - {e}"
                    )

    async def _save_work_episodes_with_progress(
        self,
        work_episodes_by_file: Dict[str, List],
        batch_size: int,
        max_concurrent: int,
    ) -> None:
        """
        work/ディレクトリのエピソードを保存する

        Args:
            work_episodes_by_file: ファイルパスとエピソードリストの辞書
            batch_size: バッチサイズ（互換性のため保持）
            max_concurrent: 最大同時実行数
        """
        # ファイルごとにエピソード保存を実行
        for file_path, file_episodes in work_episodes_by_file.items():
            await self._save_file_episodes_with_progress(
                file_path, file_episodes, batch_size, max_concurrent
            )

    def _extract_source_file_from_episode(self, episode, documents: List) -> str:
        """
        エピソードから元ファイルパスを抽出する

        Args:
            episode: エピソード
            documents: ドキュメントリスト

        Returns:
            str: 元ファイルパス
        """
        # エピソード名からファイル名を抽出（例: "sample.pdf - chunk 0" -> "sample.pdf"）
        episode_name = episode.name

        # ドキュメントリストから対応するファイルパスを探す
        for doc in documents:
            file_name = Path(doc.file_path).name
            if file_name in episode_name:
                return doc.file_path

        # 見つからない場合はエピソード名をそのまま使用
        return episode_name.split(" - ")[0] if " - " in episode_name else episode_name
