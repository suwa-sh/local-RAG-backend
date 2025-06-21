"""FileSystemDocumentReader - ファイルシステムからの読み込み"""

import logging
import shutil
from pathlib import Path
from typing import List
from src.domain.document import Document


class FileSystemDocumentReader:
    """ファイルシステムからドキュメントを読み込むリーダー"""

    def __init__(self, base_directory: str | None = None) -> None:
        """
        FileSystemDocumentReaderを初期化する

        Args:
            base_directory: 相対パス計算の基準ディレクトリ
        """
        self._logger = logging.getLogger(__name__)
        self._base_directory = base_directory

    def list_supported_files(self, directory: str) -> List[str]:
        """
        指定ディレクトリ内のサポート対象ファイルを再帰的に検索する

        Args:
            directory: 検索対象ディレクトリのパス

        Returns:
            List[str]: サポート対象ファイルパスのリスト

        Raises:
            FileNotFoundError: ディレクトリが存在しない場合
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            raise FileNotFoundError(f"ディレクトリが見つかりません: {directory}")

        file_paths = []

        # 再帰的にファイルを検索
        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue

            # ファイル拡張子を取得
            file_extension = file_path.suffix.lstrip(".").lower()

            # サポート対象ファイルタイプかチェック
            if file_extension in Document.SUPPORTED_FILE_TYPES:
                file_paths.append(str(file_path))

        return file_paths

    def read_document(
        self, file_path: str, base_directory: str | None = None
    ) -> Document:
        """
        指定ファイルパスからDocumentを読み込む

        Args:
            file_path: 読み込むファイルのパス
            base_directory: 相対パス計算の基準ディレクトリ（Noneの場合はファイル名のみ使用）

        Returns:
            Document: 読み込まれたドキュメント

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: サポートされていないファイルタイプの場合
        """
        return Document.from_file(file_path, base_directory)

    def read_documents(
        self, file_paths: List[str], base_directory: str | None = None
    ) -> List[Document]:
        """
        複数のファイルパスからDocumentリストを読み込む

        Args:
            file_paths: 読み込むファイルパスのリスト
            base_directory: 相対パス計算の基準ディレクトリ（Noneの場合はファイル名のみ使用）

        Returns:
            List[Document]: 読み込まれたドキュメントのリスト

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: サポートされていないファイルタイプの場合
        """
        if not file_paths:
            return []

        documents = []
        for file_path in file_paths:
            document = self.read_document(file_path, base_directory)

            # ファイルサイズをチェックして大きなファイルの警告を出力
            self._check_file_size(file_path)

            documents.append(document)

        return documents

    def _check_file_size(self, file_path: str) -> None:
        """
        ファイルサイズをチェックして大きなファイルに対する警告を出力

        Args:
            file_path: チェック対象のファイルパス
        """
        try:
            file_size = Path(file_path).stat().st_size
            file_size_mb = file_size / (1024 * 1024)  # MB変換

            if file_size_mb > 100:  # 100MB以上の場合
                self._logger.warning(
                    f"⚠️ 大きなファイル検出: {Path(file_path).name} "
                    f"({file_size_mb:.1f}MB) - メモリ使用量にご注意ください"
                )
            elif file_size_mb > 50:  # 50MB以上の場合は情報ログ
                self._logger.info(
                    f"📄 大きめのファイル: {Path(file_path).name} ({file_size_mb:.1f}MB)"
                )
        except OSError as e:
            self._logger.debug(f"ファイルサイズ取得失敗: {file_path} - {e}")

    def move_file(self, source_path: str, destination_directory: str) -> str:
        """
        ファイルを指定ディレクトリに移動する（ディレクトリ構造を維持）

        Args:
            source_path: 移動元ファイルパス
            destination_directory: 移動先ディレクトリ

        Returns:
            str: 移動後のファイルパス

        Raises:
            FileNotFoundError: 移動元ファイルが存在しない場合
            OSError: ファイル移動に失敗した場合
        """
        source = Path(source_path)
        dest_base_dir = Path(destination_directory)

        if not source.exists():
            raise FileNotFoundError(f"移動元ファイルが存在しません: {source_path}")

        # ディレクトリ構造を維持して移動先パスを構築
        if self._base_directory:
            # 基準ディレクトリからの相対パスを取得
            try:
                relative_path = source.relative_to(Path(self._base_directory))
                destination_path = dest_base_dir / relative_path
            except ValueError:
                # 相対パス計算に失敗した場合はファイル名のみ使用
                self._logger.warning(
                    f"⚠️ 相対パス計算失敗: {source_path} (基準: {self._base_directory})"
                )
                destination_path = dest_base_dir / source.name
        else:
            # 基準ディレクトリが指定されていない場合はファイル名のみ使用
            destination_path = dest_base_dir / source.name

        # 移動先ディレクトリを作成
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        # 同名ファイルが既に存在する場合のハンドリング
        if destination_path.exists():
            # タイムスタンプ付きの名前で回避
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = destination_path.stem
            suffix = destination_path.suffix
            destination_path = destination_path.parent / f"{stem}_{timestamp}{suffix}"

        try:
            shutil.move(str(source), str(destination_path))
            self._logger.info(
                f"📁 ファイル移動完了: {source.name} → {destination_path.relative_to(dest_base_dir)}"
            )

            # 移動元のディレクトリが空になった場合は削除
            self._cleanup_empty_directories(source.parent)

            return str(destination_path)

        except OSError as e:
            self._logger.error(
                f"❌ ファイル移動失敗: {source_path} → {destination_directory} - {e}"
            )
            raise

    def _cleanup_empty_directories(self, directory: Path) -> None:
        """
        空のディレクトリを再帰的に削除する（base_directoryまでは削除しない）

        Args:
            directory: 削除対象のディレクトリ
        """
        if not directory.exists() or not directory.is_dir():
            return

        # base_directoryの親ディレクトリ以下のディレクトリのみ削除対象
        # （input/, work/, done/ すべてを対象にするため）
        if self._base_directory:
            base_path = Path(self._base_directory)
            # base_directoryの親ディレクトリを基準とする（例: /app/data）
            root_path = base_path.parent
            if not directory.is_relative_to(root_path):
                return
            # base_directoryそのものは削除しない
            if directory == base_path:
                return

        try:
            # ディレクトリが空の場合に削除（base_directoryとroot_path以外）
            if not any(directory.iterdir()):
                directory.rmdir()
                self._logger.debug(f"🗑️ 空ディレクトリ削除: {directory}")

                # 親ディレクトリも確認（再帰的）
                self._cleanup_empty_directories(directory.parent)

        except OSError as e:
            self._logger.debug(f"ディレクトリ削除失敗: {directory} - {e}")
