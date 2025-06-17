"""FileSystemDocumentReader - ファイルシステムからの読み込み"""

from pathlib import Path
from typing import List
from src.domain.document import Document


class FileSystemDocumentReader:
    """ファイルシステムからドキュメントを読み込むリーダー"""

    def __init__(self) -> None:
        """FileSystemDocumentReaderを初期化する"""
        pass

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
            documents.append(document)

        return documents
