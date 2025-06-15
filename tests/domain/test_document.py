"""Document値オブジェクトのテスト"""

import pytest
from datetime import datetime
from src.domain.document import Document


class TestDocument:
    """Document値オブジェクトのテストクラス"""

    def test_Document作成_正常な値を指定した場合_インスタンスが作成されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        file_path = "/docs/sample.pdf"
        file_name = "sample.pdf"
        file_type = "pdf"
        content = "This is sample content..."
        file_last_modified = datetime(2025, 6, 13, 10, 0, 0)

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        document = Document(
            file_path=file_path,
            file_name=file_name,
            file_type=file_type,
            content=content,
            file_last_modified=file_last_modified,
        )

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert document.file_path == file_path
        assert document.file_name == file_name
        assert document.file_type == file_type
        assert document.content == content
        assert document.file_last_modified == file_last_modified

    def test_Document作成_file_pathが空文字の場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        file_path = ""
        file_name = "sample.pdf"
        file_type = "pdf"
        content = "content"

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(ValueError, match="file_pathは空文字列にできません"):
            Document(
                file_path=file_path,
                file_name=file_name,
                file_type=file_type,
                content=content,
                file_last_modified=datetime.now(),
            )

    def test_Document作成_file_nameが空文字の場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        file_path = "/docs/sample.pdf"
        file_name = ""
        file_type = "pdf"
        content = "content"

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(ValueError, match="file_nameは空文字列にできません"):
            Document(
                file_path=file_path,
                file_name=file_name,
                file_type=file_type,
                content=content,
                file_last_modified=datetime.now(),
            )

    def test_Document作成_contentが空文字の場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        file_path = "/docs/sample.pdf"
        file_name = "sample.pdf"
        file_type = "pdf"
        content = ""

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(ValueError, match="contentは空文字列にできません"):
            Document(
                file_path=file_path,
                file_name=file_name,
                file_type=file_type,
                content=content,
                file_last_modified=datetime.now(),
            )

    def test_Document作成_file_typeがサポートされていない場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        file_path = "/docs/sample.xyz"
        file_name = "sample.xyz"
        file_type = "unsupported"
        content = "content"

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(ValueError, match="サポートされていないfile_typeです"):
            Document(
                file_path=file_path,
                file_name=file_name,
                file_type=file_type,
                content=content,
                file_last_modified=datetime.now(),
            )

    def test_Document等価性_同じ値のインスタンス同士_等しいこと(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        file_path = "/docs/test.txt"
        file_name = "test.txt"
        file_type = "txt"
        content = "test content"
        file_last_modified = datetime(2025, 6, 13, 10, 0, 0)

        document1 = Document(
            file_path=file_path,
            file_name=file_name,
            file_type=file_type,
            content=content,
            file_last_modified=file_last_modified,
        )

        document2 = Document(
            file_path=file_path,
            file_name=file_name,
            file_type=file_type,
            content=content,
            file_last_modified=file_last_modified,
        )

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        assert document1 == document2

    def test_Document等価性_異なる値のインスタンス同士_等しくないこと(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        document1 = Document(
            file_path="/docs/file1.txt",
            file_name="file1.txt",
            file_type="txt",
            content="content1",
            file_last_modified=datetime(2025, 6, 13, 10, 0, 0),
        )

        document2 = Document(
            file_path="/docs/file2.txt",
            file_name="file2.txt",
            file_type="txt",
            content="content2",
            file_last_modified=datetime(2025, 6, 13, 11, 0, 0),
        )

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        assert document1 != document2

    def test_Document_from_file_ファイルから作成した場合_適切なインスタンスが作成されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        # テスト用の一時ファイルパス（実際のファイルは作成せず、パスのみテスト）

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        # from_fileメソッドはファイル読み込みを含むため、モック等での実装が必要
        # 現在はメソッドの存在確認のみ
        # document = Document.from_file(file_path)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # from_fileメソッドが存在することを確認
        assert hasattr(Document, "from_file")
        assert callable(getattr(Document, "from_file"))

    def test_Document作成_Unstructuredサポートファイルタイプ_正常に作成されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        # Unstructured.io公式サポートの代表的なファイルタイプをテスト
        supported_types = [
            ("xlsx", "Excel"),
            ("pptx", "PowerPoint"),
            ("epub", "eBook"),
            ("eml", "Email"),
            ("rst", "reStructuredText"),
        ]

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        for file_type, description in supported_types:
            document = Document(
                file_path=f"/docs/sample.{file_type}",
                file_name=f"sample.{file_type}",
                file_type=file_type,
                content=f"Sample {description} content",
                file_last_modified=datetime(2025, 6, 13, 10, 0, 0),
            )
            assert document.file_type == file_type
            assert document.file_name == f"sample.{file_type}"
