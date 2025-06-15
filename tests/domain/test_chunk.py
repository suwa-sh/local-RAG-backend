"""Chunk値オブジェクトのテスト"""

import pytest
from datetime import datetime
from src.domain.chunk import Chunk
from src.domain.document import Document
from src.domain.group_id import GroupId


class TestChunk:
    """Chunk値オブジェクトのテストクラス"""

    def test_Chunk作成_正常な値を指定した場合_インスタンスが作成されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        chunk_id = "sample_pdf_chunk_0"
        text = "This is the first chunk..."
        metadata = {"original_chunk_id": "chunk_0", "position": 0}
        source_document = Document(
            file_path="/docs/sample.pdf",
            file_name="sample.pdf",
            file_type="pdf",
            content="This is sample content...",
            file_last_modified=datetime(2025, 6, 13, 10, 0, 0),
        )

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        chunk = Chunk(
            id=chunk_id,
            text=text,
            metadata=metadata,
            source_document=source_document,
        )

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert chunk.id == chunk_id
        assert chunk.text == text
        assert chunk.metadata == metadata
        assert chunk.source_document == source_document

    def test_Chunk作成_idが空文字の場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        chunk_id = ""
        text = "Some text"
        metadata = {"position": 0}
        source_document = Document(
            file_path="/docs/test.txt",
            file_name="test.txt",
            file_type="txt",
            content="content",
            file_last_modified=datetime(2025, 6, 13, 10, 0, 0),
        )

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(ValueError, match="idは空文字列にできません"):
            Chunk(
                id=chunk_id,
                text=text,
                metadata=metadata,
                source_document=source_document,
            )

    def test_Chunk作成_textが空文字の場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        chunk_id = "chunk_1"
        text = ""
        metadata = {"position": 0}
        source_document = Document(
            file_path="/docs/test.txt",
            file_name="test.txt",
            file_type="txt",
            content="content",
            file_last_modified=datetime(2025, 6, 13, 10, 0, 0),
        )

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(ValueError, match="textは空文字列にできません"):
            Chunk(
                id=chunk_id,
                text=text,
                metadata=metadata,
                source_document=source_document,
            )

    def test_Chunk等価性_同じ値のインスタンス同士_等しいこと(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        chunk_id = "chunk_test"
        text = "Test chunk text"
        metadata = {"position": 1}
        source_document = Document(
            file_path="/docs/test.txt",
            file_name="test.txt",
            file_type="txt",
            content="test content",
            file_last_modified=datetime(2025, 6, 13, 10, 0, 0),
        )

        chunk1 = Chunk(
            id=chunk_id,
            text=text,
            metadata=metadata,
            source_document=source_document,
        )

        chunk2 = Chunk(
            id=chunk_id,
            text=text,
            metadata=metadata,
            source_document=source_document,
        )

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        assert chunk1 == chunk2

    def test_Chunk等価性_異なる値のインスタンス同士_等しくないこと(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        source_document = Document(
            file_path="/docs/test.txt",
            file_name="test.txt",
            file_type="txt",
            content="test content",
            file_last_modified=datetime(2025, 6, 13, 10, 0, 0),
        )

        chunk1 = Chunk(
            id="chunk_1",
            text="text1",
            metadata={"position": 0},
            source_document=source_document,
        )

        chunk2 = Chunk(
            id="chunk_2",
            text="text2",
            metadata={"position": 1},
            source_document=source_document,
        )

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        assert chunk1 != chunk2

    def test_Chunk_to_episode_GroupIdを指定した場合_適切なEpisodeが作成されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        chunk_id = "sample_chunk"
        text = "This is chunk content for episode"
        metadata = {"position": 0}
        file_last_modified = datetime(2025, 6, 13, 15, 30, 45)
        source_document = Document(
            file_path="/docs/sample.pdf",
            file_name="sample.pdf",
            file_type="pdf",
            content="original content",
            file_last_modified=file_last_modified,
        )
        group_id = GroupId("default")

        chunk = Chunk(
            id=chunk_id,
            text=text,
            metadata=metadata,
            source_document=source_document,
        )

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        episode = chunk.to_episode(group_id)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert episode.name == f"{source_document.file_name} - {chunk_id}"
        assert episode.body == text
        assert episode.source_description == f"Source file: {source_document.file_name}"
        assert episode.episode_type == "text"
        assert episode.group_id == group_id
        # reference_timeはファイルの更新日時と同じであることを確認
        assert episode.reference_time == file_last_modified

    def test_Chunkハッシュ_同じ値のインスタンス同士_同じハッシュ値であること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        chunk_id = "hash_test_chunk"
        text = "Hash test text"
        metadata = {"position": 2}
        source_document = Document(
            file_path="/docs/hash_test.txt",
            file_name="hash_test.txt",
            file_type="txt",
            content="hash test content",
            file_last_modified=datetime(2025, 6, 13, 10, 0, 0),
        )

        chunk1 = Chunk(
            id=chunk_id,
            text=text,
            metadata=metadata,
            source_document=source_document,
        )

        chunk2 = Chunk(
            id=chunk_id,
            text=text,
            metadata=metadata,
            source_document=source_document,
        )

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        assert hash(chunk1) == hash(chunk2)
