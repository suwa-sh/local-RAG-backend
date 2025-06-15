"""FileSystemDocumentReaderのテスト"""

import pytest
from unittest.mock import patch
from pathlib import Path
from datetime import datetime

from src.adapter.filesystem_document_reader import FileSystemDocumentReader
from src.domain.document import Document


class TestFileSystemDocumentReader:
    """FileSystemDocumentReaderのテストクラス"""

    def test_FileSystemDocumentReader初期化_インスタンスが作成されること(self):
        # ------------------------------
        # 準備 (Arrange) & 実行 (Act)
        # ------------------------------
        reader = FileSystemDocumentReader()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert reader is not None

    def test_list_supported_files_サポート対象ファイルのあるディレクトリを指定した場合_ファイルパスリストが返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        reader = FileSystemDocumentReader()
        directory = "/docs"

        # モックファイル（サポート対象と非対象の混在）
        mock_files = [
            Path("/docs/document.pdf"),
            Path("/docs/text.txt"),
            Path("/docs/presentation.pptx"),
            Path("/docs/image.png"),
            Path("/docs/unsupported.xyz"),  # サポート外
            Path("/docs/script.py"),  # サポート外
        ]

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch("src.adapter.filesystem_document_reader.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch(
                "src.adapter.filesystem_document_reader.Path.rglob"
            ) as mock_rglob:
                mock_rglob.return_value = mock_files
                with patch(
                    "src.adapter.filesystem_document_reader.Path.is_file"
                ) as mock_is_file:
                    mock_is_file.return_value = True
                    file_paths = reader.list_supported_files(directory)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert len(file_paths) == 4  # サポート対象のみ
        assert "/docs/document.pdf" in file_paths
        assert "/docs/text.txt" in file_paths
        assert "/docs/presentation.pptx" in file_paths
        assert "/docs/image.png" in file_paths
        assert "/docs/unsupported.xyz" not in file_paths
        assert "/docs/script.py" not in file_paths

    def test_list_supported_files_空のディレクトリを指定した場合_空のリストが返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        reader = FileSystemDocumentReader()
        directory = "/empty"

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch("src.adapter.filesystem_document_reader.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch(
                "src.adapter.filesystem_document_reader.Path.rglob"
            ) as mock_rglob:
                mock_rglob.return_value = []
                file_paths = reader.list_supported_files(directory)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert len(file_paths) == 0

    def test_list_supported_files_存在しないディレクトリを指定した場合_例外が発生すること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        reader = FileSystemDocumentReader()
        directory = "/nonexistent"

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with patch("src.adapter.filesystem_document_reader.Path.exists") as mock_exists:
            mock_exists.return_value = False

            with pytest.raises(FileNotFoundError, match="ディレクトリが見つかりません"):
                reader.list_supported_files(directory)

    def test_read_document_テキストファイルを読み込んだ場合_適切なDocumentが返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        reader = FileSystemDocumentReader()
        file_path = "/docs/sample.txt"
        file_content = "This is sample text content."

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch("src.adapter.filesystem_document_reader.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch(
                "src.adapter.filesystem_document_reader.Path.read_text"
            ) as mock_read_text:
                mock_read_text.return_value = file_content
                with patch(
                    "src.adapter.filesystem_document_reader.Path.stat"
                ) as mock_stat:
                    mock_stat.return_value.st_mtime = (
                        1672531200.0  # 2023-01-01 00:00:00
                    )
                    document = reader.read_document(file_path)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert isinstance(document, Document)
        assert document.file_path == file_path
        assert document.file_name == "sample.txt"
        assert document.file_type == "txt"
        assert document.content == file_content

    def test_read_document_バイナリファイルを読み込んだ場合_適切なDocumentが返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        reader = FileSystemDocumentReader()
        file_path = "/docs/sample.pdf"

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch("src.adapter.filesystem_document_reader.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch(
                "src.adapter.filesystem_document_reader.Path.read_text"
            ) as mock_read_text:
                mock_read_text.side_effect = UnicodeDecodeError(
                    "utf-8", b"", 0, 1, "error"
                )
                with patch(
                    "src.adapter.filesystem_document_reader.Path.stat"
                ) as mock_stat:
                    mock_stat.return_value.st_mtime = (
                        1672531200.0  # 2023-01-01 00:00:00
                    )
                    document = reader.read_document(file_path)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert isinstance(document, Document)
        assert document.file_path == file_path
        assert document.file_name == "sample.pdf"
        assert document.file_type == "pdf"
        assert "<バイナリファイル: sample.pdf>" in document.content

    def test_read_document_存在しないファイルを指定した場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        reader = FileSystemDocumentReader()
        file_path = "/docs/nonexistent.txt"

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with patch("src.adapter.filesystem_document_reader.Path.exists") as mock_exists:
            mock_exists.return_value = False

            with pytest.raises(FileNotFoundError, match="ファイルが見つかりません"):
                reader.read_document(file_path)

    def test_read_document_サポートされていないファイルタイプを指定した場合_例外が発生すること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        reader = FileSystemDocumentReader()
        file_path = "/docs/unsupported.xyz"

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with patch("src.adapter.filesystem_document_reader.Path.exists") as mock_exists:
            mock_exists.return_value = True

            with pytest.raises(ValueError, match="サポートされていないfile_typeです"):
                reader.read_document(file_path)

    def test_read_documents_複数ファイルを一括読み込みした場合_適切なDocumentリストが返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        reader = FileSystemDocumentReader()
        file_paths = ["/docs/file1.txt", "/docs/file2.pdf", "/docs/file3.md"]

        expected_documents = [
            Document(
                "/docs/file1.txt",
                "file1.txt",
                "txt",
                "Content 1",
                datetime(2025, 6, 13, 10, 0, 0),
            ),
            Document(
                "/docs/file2.pdf",
                "file2.pdf",
                "pdf",
                "<バイナリファイル: file2.pdf>",
                datetime(2025, 6, 13, 11, 0, 0),
            ),
            Document(
                "/docs/file3.md",
                "file3.md",
                "md",
                "# Content 3",
                datetime(2025, 6, 13, 12, 0, 0),
            ),
        ]

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch.object(reader, "read_document") as mock_read_document:
            mock_read_document.side_effect = expected_documents
            documents = reader.read_documents(file_paths)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert len(documents) == 3
        assert mock_read_document.call_count == 3
        for i, doc in enumerate(documents):
            assert doc == expected_documents[i]

    def test_read_documents_空のリストを指定した場合_空のリストが返されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        reader = FileSystemDocumentReader()
        file_paths = []

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        documents = reader.read_documents(file_paths)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert len(documents) == 0
