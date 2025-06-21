"""ChunkFileManager - チャンクファイルの管理"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from src.domain.chunk import Chunk


class ChunkFileManager:
    """チャンクファイルの保存・読み込み・削除を管理するクラス"""

    def __init__(self, chunks_directory: str = "data/input_chunks") -> None:
        """
        ChunkFileManagerを初期化する

        Args:
            chunks_directory: チャンクファイルを保存するディレクトリ
        """
        self._chunks_directory = Path(chunks_directory)
        self._logger = logging.getLogger(__name__)

        # ディレクトリを作成（存在しない場合）
        self._chunks_directory.mkdir(parents=True, exist_ok=True)

    def _get_chunk_directory(self, file_path: str) -> Path:
        """
        ファイルパスに対応するチャンクディレクトリを取得する

        Args:
            file_path: 元ファイルパス

        Returns:
            Path: チャンクディレクトリのパス
        """
        # /input/ または /input_work/ から始まる相対パスを抽出
        relative_path = file_path
        for prefix in ["/input/", "/input_work/"]:
            if prefix in file_path:
                # 最後に出現するプレフィックスの後ろ部分を取得
                parts = file_path.split(prefix)
                if len(parts) >= 2:
                    relative_path = prefix.join(parts[-1:])
                break

        # data/input_chunks/相対パス/
        return self._chunks_directory / relative_path

    def _get_metadata_file_path(self, file_path: str) -> Path:
        """
        メタデータファイルのパスを取得する

        Args:
            file_path: 元ファイルパス

        Returns:
            Path: メタデータファイルのパス
        """
        chunk_dir = self._get_chunk_directory(file_path)
        return chunk_dir / "metadata.json"

    def _get_chunk_file_path(self, file_path: str, position: int) -> Path:
        """
        チャンクファイルのパスを取得する

        Args:
            file_path: 元ファイルパス
            position: チャンクの位置

        Returns:
            Path: チャンクファイルのパス
        """
        chunk_dir = self._get_chunk_directory(file_path)
        return chunk_dir / f"chunk_{position}.json"

    def _get_episode_file_path(self, file_path: str, episode_index: int) -> Path:
        """
        エピソードファイルのパスを取得する

        Args:
            file_path: 元ファイルパス
            episode_index: エピソードのインデックス

        Returns:
            Path: エピソードファイルのパス
        """
        chunk_dir = self._get_chunk_directory(file_path)
        return chunk_dir / f"episode_{episode_index}.json"

    def has_chunk_files(self, file_path: str) -> bool:
        """
        指定ファイルのチャンクファイルが存在するかチェックする

        Args:
            file_path: 元ファイルパス

        Returns:
            bool: チャンクファイルが存在する場合True
        """
        metadata_file = self._get_metadata_file_path(file_path)
        return metadata_file.exists()

    def save_chunks(
        self,
        chunks: List[Chunk],
        file_path: str,
        last_processed_position: int = -1,
        error_message: str = "",
    ) -> None:
        """
        チャンクリストをファイルに保存する

        Args:
            chunks: 保存するチャンクのリスト
            file_path: 元ファイルパス
            last_processed_position: 最後に処理された位置（-1の場合は未処理）
            error_message: エラーメッセージ

        Raises:
            OSError: ファイル保存に失敗した場合
        """
        if not chunks:
            self._logger.warning(f"保存対象のチャンクがありません: {file_path}")
            return

        chunk_dir = self._get_chunk_directory(file_path)
        chunk_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 各チャンクを個別ファイルに保存
            for chunk in chunks:
                position = chunk.metadata.get("position", 0)
                chunk_file = self._get_chunk_file_path(file_path, position)

                with open(chunk_file, "w", encoding="utf-8") as f:
                    f.write(chunk.to_json())

            # メタデータファイルを保存
            metadata = {
                "original_file": file_path,
                "total_chunks": len(chunks),
                "last_processed_position": last_processed_position,
                "created_at": datetime.now().isoformat(),
                "error_message": error_message,
            }

            metadata_file = self._get_metadata_file_path(file_path)
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            self._logger.info(
                f"💾 チャンク保存完了: {file_path} "
                f"({len(chunks)}チャンク, 処理位置: {last_processed_position})"
            )

        except OSError as e:
            self._logger.error(f"❌ チャンク保存失敗: {file_path} - {e}")
            raise

    def load_chunks(self, file_path: str) -> Tuple[List[Chunk], Dict[str, Any]]:
        """
        ファイルパスに対応するチャンクを読み込む

        Args:
            file_path: 元ファイルパス

        Returns:
            Tuple[List[Chunk], Dict[str, Any]]: (チャンクリスト, メタデータ)

        Raises:
            FileNotFoundError: チャンクファイルが存在しない場合
            OSError: ファイル読み込みに失敗した場合
            json.JSONDecodeError: JSON解析に失敗した場合
        """
        metadata_file = self._get_metadata_file_path(file_path)

        if not metadata_file.exists():
            raise FileNotFoundError(f"チャンクファイルが存在しません: {file_path}")

        try:
            # メタデータを読み込み
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # 各チャンクファイルを読み込み
            chunks = []
            total_chunks = metadata.get("total_chunks", 0)

            for position in range(total_chunks):
                chunk_file = self._get_chunk_file_path(file_path, position)

                if chunk_file.exists():
                    with open(chunk_file, "r", encoding="utf-8") as f:
                        chunk_json = f.read()
                        chunk = Chunk.from_json(chunk_json)
                        chunks.append(chunk)
                else:
                    self._logger.warning(
                        f"⚠️ チャンクファイルが見つかりません: {chunk_file}"
                    )

            self._logger.info(
                f"📁 チャンク読み込み完了: {file_path} "
                f"({len(chunks)}/{total_chunks}チャンク)"
            )

            return chunks, metadata

        except (OSError, json.JSONDecodeError) as e:
            self._logger.error(f"❌ チャンク読み込み失敗: {file_path} - {e}")
            raise

    def delete_all_chunks(self, file_path: str) -> None:
        """
        指定ファイルのすべてのチャンクファイルを削除する

        Args:
            file_path: 元ファイルパス
        """
        chunk_dir = self._get_chunk_directory(file_path)

        if chunk_dir.exists():
            try:
                # ディレクトリ内のすべてのファイルを削除
                for file in chunk_dir.iterdir():
                    if file.is_file():
                        file.unlink()

                # ディレクトリ自体を削除
                chunk_dir.rmdir()

                self._logger.info(f"🗑️ チャンクディレクトリ削除完了: {chunk_dir}")

            except OSError as e:
                self._logger.warning(
                    f"⚠️ チャンクディレクトリ削除失敗: {chunk_dir} - {e}"
                )

    def get_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        指定ファイルのメタデータを取得する

        Args:
            file_path: 元ファイルパス

        Returns:
            Optional[Dict[str, Any]]: メタデータ（存在しない場合はNone）
        """
        metadata_file = self._get_metadata_file_path(file_path)

        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self._logger.warning(f"⚠️ メタデータ読み込み失敗: {file_path} - {e}")
            return None

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        チャンクキャッシュの統計情報を取得する

        Returns:
            Dict[str, Any]: 統計情報
        """
        if not self._chunks_directory.exists():
            return {"total_cached_files": 0, "total_chunks": 0, "total_size_mb": 0.0}

        total_files = 0
        total_chunks = 0
        total_size = 0

        for chunk_dir in self._chunks_directory.iterdir():
            if chunk_dir.is_dir():
                total_files += 1

                dir_total_chunks, dir_total_size = self._aggregate_chunk_data(chunk_dir)
                total_chunks += dir_total_chunks
                total_size += dir_total_size

        return {
            "total_cached_files": total_files,
            "total_chunks": total_chunks,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }

    def _aggregate_chunk_data(self, chunk_dir):
        total_chunks = 0
        total_size = 0
        for chunk_file in chunk_dir.iterdir():
            if chunk_file.is_file() and chunk_file.suffix == ".json":
                if chunk_file.name.startswith("chunk_"):
                    total_chunks += 1
                total_size += chunk_file.stat().st_size
        return total_chunks, total_size

    # ===== エピソードデータ永続化管理 =====

    def save_episodes(
        self,
        file_path: str,
        episodes: List,
        start_index: int = 0,
    ) -> None:
        """
        エピソードリストをファイルに保存する

        Args:
            file_path: 元ファイルパス
            episodes: 保存するエピソードのリスト
            start_index: 開始インデックス

        Raises:
            OSError: ファイル保存に失敗した場合
        """
        if not episodes:
            self._logger.warning(f"保存対象のエピソードがありません: {file_path}")
            return

        chunk_dir = self._get_chunk_directory(file_path)
        chunk_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 各エピソードを個別ファイルに保存
            for i, episode in enumerate(episodes):
                episode_index = start_index + i
                episode_file = self._get_episode_file_path(file_path, episode_index)

                # エピソードを辞書形式に変換
                episode_data = {
                    "name": episode.name,
                    "body": episode.body,
                    "source_description": episode.source_description,
                    "reference_time": episode.reference_time.isoformat()
                    if episode.reference_time
                    else None,
                    "episode_type": episode.episode_type,
                    "group_id": episode.group_id.value,
                }

                with open(episode_file, "w", encoding="utf-8") as f:
                    json.dump(episode_data, f, ensure_ascii=False, indent=2)

            self._logger.info(
                f"💾 エピソードファイル保存完了: {file_path} "
                f"({len(episodes)}エピソード, インデックス: {start_index}〜{start_index + len(episodes) - 1})"
            )

        except OSError as e:
            self._logger.error(f"❌ エピソードファイル保存失敗: {file_path} - {e}")
            raise

    def load_episodes(
        self,
        file_path: str,
        start_index: int = 0,
        end_index: Optional[int] = None,
    ) -> List:
        """
        指定範囲のエピソードファイルを読み込む

        Args:
            file_path: 元ファイルパス
            start_index: 開始インデックス
            end_index: 終了インデックス（Noneの場合は存在するファイルまで）

        Returns:
            List: エピソードリスト

        Raises:
            FileNotFoundError: エピソードファイルが存在しない場合
            OSError: ファイル読み込みに失敗した場合
            json.JSONDecodeError: JSON解析に失敗した場合
        """
        from src.domain.episode import Episode
        from src.domain.group_id import GroupId

        episodes = []

        try:
            # end_indexが指定されていない場合は、存在するファイルを探索
            if end_index is None:
                end_index = start_index + 1000  # 上限を設定して無限ループを防ぐ

            for episode_index in range(start_index, end_index + 1):
                episode_file = self._get_episode_file_path(file_path, episode_index)

                if not episode_file.exists():
                    # end_indexが指定されていない場合は、ファイルが見つからなくなったら終了
                    if end_index == start_index + 1000:
                        break
                    # end_indexが指定されている場合は警告
                    self._logger.warning(
                        f"⚠️ エピソードファイルが見つかりません: {episode_file}"
                    )
                    continue

                with open(episode_file, "r", encoding="utf-8") as f:
                    episode_data = json.load(f)

                # エピソードオブジェクトを復元
                episode = Episode(
                    name=episode_data["name"],
                    body=episode_data["body"],
                    source_description=episode_data["source_description"],
                    reference_time=datetime.fromisoformat(
                        episode_data["reference_time"]
                    )
                    if episode_data.get("reference_time")
                    else None,
                    episode_type=episode_data["episode_type"],
                    group_id=GroupId(episode_data["group_id"]),
                )
                episodes.append(episode)

            self._logger.info(
                f"📁 エピソードファイル読み込み完了: {file_path} "
                f"({len(episodes)}エピソード, インデックス: {start_index}〜{start_index + len(episodes) - 1})"
            )

            return episodes

        except (OSError, json.JSONDecodeError) as e:
            self._logger.error(f"❌ エピソードファイル読み込み失敗: {file_path} - {e}")
            raise

    def has_saved_episodes(self, file_path: str) -> bool:
        """
        指定ファイルの保存済みエピソードファイルが存在するかチェックする

        Args:
            file_path: 元ファイルパス

        Returns:
            bool: エピソードファイルが存在する場合True
        """
        # チャンクディレクトリ内にエピソードファイルが存在するかチェック
        chunk_dir = self._get_chunk_directory(file_path)
        if not chunk_dir.exists():
            return False

        # episode_*.jsonファイルの存在を確認
        episode_files = list(chunk_dir.glob("episode_*.json"))
        return len(episode_files) > 0

    def delete_episode_files(
        self,
        file_path: str,
        start_index: int = 0,
        end_index: Optional[int] = None,
    ) -> None:
        """
        指定範囲のエピソードファイルを削除する

        Args:
            file_path: 元ファイルパス
            start_index: 開始インデックス
            end_index: 終了インデックス（Noneの場合は存在するファイルまで）
        """
        deleted_count = 0

        try:
            # end_indexが指定されていない場合は、存在するファイルを探索
            if end_index is None:
                end_index = start_index + 1000  # 上限を設定

            for episode_index in range(start_index, end_index + 1):
                episode_file = self._get_episode_file_path(file_path, episode_index)

                if episode_file.exists():
                    episode_file.unlink()
                    deleted_count += 1
                    self._logger.debug(f"🗑️ エピソードファイル削除: {episode_file}")
                elif end_index == start_index + 1000:
                    # 探索モードでファイルが見つからなくなったら終了
                    break

            if deleted_count > 0:
                self._logger.info(
                    f"🗑️ エピソードファイル削除完了: {file_path} "
                    f"({deleted_count}ファイル, インデックス: {start_index}〜{start_index + deleted_count - 1})"
                )

                # 削除後に空ディレクトリをクリーンアップ
                chunk_dir = self._get_chunk_directory(file_path)
                self._cleanup_empty_directories(chunk_dir)

        except OSError as e:
            self._logger.warning(f"⚠️ エピソードファイル削除失敗: {file_path} - {e}")

    def _cleanup_empty_directories(self, directory: Path) -> None:
        """
        空のディレクトリを再帰的に削除する（chunks_directoryまでは削除しない）

        Args:
            directory: 削除対象のディレクトリ
        """
        if not directory.exists() or not directory.is_dir():
            return

        # chunks_directory以下のディレクトリのみ削除対象
        if not directory.is_relative_to(self._chunks_directory):
            return

        try:
            # ディレクトリが空で、chunks_directoryではない場合に削除
            if not any(directory.iterdir()) and directory != self._chunks_directory:
                directory.rmdir()
                self._logger.debug(f"🗑️ 空ディレクトリ削除: {directory}")

                # 親ディレクトリも確認（再帰的）
                self._cleanup_empty_directories(directory.parent)

        except OSError as e:
            self._logger.debug(f"ディレクトリ削除失敗: {directory} - {e}")
