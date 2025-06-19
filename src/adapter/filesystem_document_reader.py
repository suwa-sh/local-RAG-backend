"""FileSystemDocumentReader - ファイルシステムからの読み込み"""

import logging
from pathlib import Path
from typing import List
from src.domain.document import Document


class FileSystemDocumentReader:
    """ファイルシステムからドキュメントを読み込むリーダー"""

    def __init__(self) -> None:
        """FileSystemDocumentReaderを初期化する"""
        self._logger = logging.getLogger(__name__)

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
