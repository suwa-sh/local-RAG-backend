"""UnstructuredDocumentParserのテスト"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.adapter.unstructured_document_parser import UnstructuredDocumentParser
from src.domain.document import Document
from src.domain.chunk import Chunk


class TestUnstructuredDocumentParser:
    """UnstructuredDocumentParserのテストクラス"""

    def test_parse_PDFファイルを解析した場合_適切なElementリストが返されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        parser = UnstructuredDocumentParser()
        file_path = "/docs/sample.pdf"

        # Unstructuredライブラリのモック
        mock_elements = [
            Mock(text="First paragraph text", metadata={"page_number": 1}),
            Mock(text="Second paragraph text", metadata={"page_number": 1}),
            Mock(text="Third paragraph text", metadata={"page_number": 2}),
        ]

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch(
            "src.adapter.unstructured_document_parser.partition"
        ) as mock_partition:
            mock_partition.return_value = mock_elements
            elements = parser.parse(file_path)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert len(elements) == 3
        assert elements[0].text == "First paragraph text"
        assert elements[1].text == "Second paragraph text"
        assert elements[2].text == "Third paragraph text"
        mock_partition.assert_called_once_with(filename=file_path)

    def test_parse_空のファイルを解析した場合_空のリストが返されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        parser = UnstructuredDocumentParser()
        file_path = "/docs/empty.txt"

        mock_elements = []

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch(
            "src.adapter.unstructured_document_parser.partition"
        ) as mock_partition:
            mock_partition.return_value = mock_elements
            elements = parser.parse(file_path)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert len(elements) == 0
        mock_partition.assert_called_once_with(filename=file_path)

    def test_parse_ファイルが存在しない場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        parser = UnstructuredDocumentParser()
        file_path = "/docs/nonexistent.pdf"

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with patch(
            "src.adapter.unstructured_document_parser.partition"
        ) as mock_partition:
            mock_partition.side_effect = FileNotFoundError("File not found")

            with pytest.raises(FileNotFoundError):
                parser.parse(file_path)

    def test_split_elements_適切なサイズのElementsを分割した場合_適切なChunkリストが返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        parser = UnstructuredDocumentParser()
        document = Document(
            file_path="/docs/test.txt",
            file_name="test.txt",
            file_type="txt",
            content="test content",
            file_last_modified=datetime(2025, 6, 13, 10, 0, 0),
        )

        mock_elements = [
            Mock(text="Short text 1", metadata={"page_number": 1}),
            Mock(text="Short text 2", metadata={"page_number": 1}),
            Mock(text="Another short text 3", metadata={"page_number": 2}),
        ]

        # chunk_elementsのモック（1つのチャンクに結合される想定）
        mock_chunked_elements = [
            Mock(
                text="Short text 1 Short text 2 Another short text 3",
                metadata={"page_number": 1},
            )
        ]

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch(
            "src.adapter.unstructured_document_parser.chunk_by_title"
        ) as mock_chunk_elements:
            mock_chunk_elements.return_value = mock_chunked_elements
            chunks = parser.split_elements(mock_elements, document)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert len(chunks) == 1  # 1つのチャンクが作成される
        for chunk in chunks:
            assert isinstance(chunk, Chunk)
            assert chunk.source_document == document
            assert len(chunk.text) > 0
            assert len(chunk.text) <= parser.max_characters

    def test_split_elements_長いElementを分割した場合_適切なチャンク数が作成されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        parser = UnstructuredDocumentParser(max_characters=100)  # 小さなサイズでテスト
        document = Document(
            file_path="/docs/long.txt",
            file_name="long.txt",
            file_type="txt",
            content="long content",
            file_last_modified=datetime(2025, 6, 13, 10, 0, 0),
        )

        # 長いテキストのElement（モック）
        long_text = "A" * 250  # max_charactersの2.5倍の長さ
        mock_elements = [Mock(text=long_text, metadata={"page_number": 1})]

        # chunk_elementsのモック（複数のチャンクに分割される想定）
        mock_chunked_elements = [
            Mock(text="A" * 100, metadata={"page_number": 1}),
            Mock(text="A" * 100, metadata={"page_number": 1}),
            Mock(text="A" * 50, metadata={"page_number": 1}),
        ]

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch(
            "src.adapter.unstructured_document_parser.chunk_by_title"
        ) as mock_chunk_elements:
            mock_chunk_elements.return_value = mock_chunked_elements
            chunks = parser.split_elements(mock_elements, document)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert len(chunks) == 3  # 3つのチャンクに分割される
        for chunk in chunks:
            assert len(chunk.text) <= parser.max_characters

    def test_split_elements_空のElementsを指定した場合_空のリストが返されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        parser = UnstructuredDocumentParser()
        document = Document(
            file_path="/docs/empty.txt",
            file_name="empty.txt",
            file_type="txt",
            content="empty",
            file_last_modified=datetime(2025, 6, 13, 10, 0, 0),
        )
        mock_elements = []

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        chunks = parser.split_elements(mock_elements, document)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert len(chunks) == 0
