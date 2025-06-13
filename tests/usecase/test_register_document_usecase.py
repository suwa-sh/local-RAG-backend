"""RegisterDocumentUseCaseのテスト"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.usecase.register_document_usecase import RegisterDocumentUseCase
from src.domain.document import Document
from src.domain.chunk import Chunk
from src.domain.episode import Episode
from src.domain.group_id import GroupId


class TestRegisterDocumentUseCase:
    """RegisterDocumentUseCaseのテストクラス"""

    def test_RegisterDocumentUseCase初期化_必要なアダプターを指定した場合_インスタンスが作成されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        file_reader = Mock()
        doc_parser = Mock()
        episode_repository = Mock()

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        usecase = RegisterDocumentUseCase(
            file_reader=file_reader,
            document_parser=doc_parser,
            episode_repository=episode_repository,
        )

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert usecase is not None
        assert usecase._file_reader == file_reader
        assert usecase._document_parser == doc_parser
        assert usecase._episode_repository == episode_repository

    @pytest.mark.asyncio
    async def test_execute_正常なディレクトリを指定した場合_ドキュメントが正常に登録されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        group_id = GroupId("test-group")
        directory = "/docs"

        # モックの準備
        file_reader = Mock()
        doc_parser = Mock()
        episode_repository = AsyncMock()

        # ファイル一覧のモック
        file_paths = ["/docs/file1.txt", "/docs/file2.pdf"]
        file_reader.list_supported_files.return_value = file_paths

        # ドキュメント読み込みのモック
        documents = [
            Document("/docs/file1.txt", "file1.txt", "txt", "Content 1"),
            Document("/docs/file2.pdf", "file2.pdf", "pdf", "Content 2"),
        ]
        file_reader.read_documents.return_value = documents

        # パース結果のモック
        elements_1 = [Mock(text="Element 1")]
        elements_2 = [Mock(text="Element 2")]
        doc_parser.parse.side_effect = [elements_1, elements_2]

        # チャンク分割結果のモック
        chunks_1 = [
            Chunk("file1_chunk_0", "Chunk 1", {}, documents[0]),
        ]
        chunks_2 = [
            Chunk("file2_chunk_0", "Chunk 2", {}, documents[1]),
        ]
        doc_parser.split_elements.side_effect = [chunks_1, chunks_2]

        usecase = RegisterDocumentUseCase(
            file_reader=file_reader,
            document_parser=doc_parser,
            episode_repository=episode_repository,
        )

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        result = await usecase.execute(group_id, directory)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # ファイル一覧取得の確認
        file_reader.list_supported_files.assert_called_once_with(directory)

        # ドキュメント読み込みの確認
        file_reader.read_documents.assert_called_once_with(file_paths)

        # パース処理の確認
        assert doc_parser.parse.call_count == 2
        doc_parser.parse.assert_any_call("/docs/file1.txt")
        doc_parser.parse.assert_any_call("/docs/file2.pdf")

        # チャンク分割の確認
        assert doc_parser.split_elements.call_count == 2
        doc_parser.split_elements.assert_any_call(elements_1, documents[0])
        doc_parser.split_elements.assert_any_call(elements_2, documents[1])

        # エピソード保存の確認
        assert episode_repository.save_batch.call_count == 1
        saved_episodes = episode_repository.save_batch.call_args[0][0]
        assert len(saved_episodes) == 2
        assert all(isinstance(ep, Episode) for ep in saved_episodes)
        assert all(ep.group_id == group_id for ep in saved_episodes)

        # 結果の確認
        assert result.total_files == 2
        assert result.total_chunks == 2
        assert result.total_episodes == 2
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_空のディレクトリを指定した場合_適切な結果が返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        group_id = GroupId("test-group")
        directory = "/empty"

        file_reader = Mock()
        doc_parser = Mock()
        episode_repository = AsyncMock()

        # 空のファイル一覧
        file_reader.list_supported_files.return_value = []
        file_reader.read_documents.return_value = []

        usecase = RegisterDocumentUseCase(
            file_reader=file_reader,
            document_parser=doc_parser,
            episode_repository=episode_repository,
        )

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        result = await usecase.execute(group_id, directory)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        file_reader.list_supported_files.assert_called_once_with(directory)
        file_reader.read_documents.assert_called_once_with([])
        doc_parser.parse.assert_not_called()
        doc_parser.split_elements.assert_not_called()
        episode_repository.save_batch.assert_not_called()

        assert result.total_files == 0
        assert result.total_chunks == 0
        assert result.total_episodes == 0
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_ファイル読み込みでエラーが発生した場合_例外が発生すること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        group_id = GroupId("test-group")
        directory = "/error"

        file_reader = Mock()
        doc_parser = Mock()
        episode_repository = AsyncMock()

        # ファイル読み込みでエラー
        file_reader.list_supported_files.side_effect = FileNotFoundError(
            "Directory not found"
        )

        usecase = RegisterDocumentUseCase(
            file_reader=file_reader,
            document_parser=doc_parser,
            episode_repository=episode_repository,
        )

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(FileNotFoundError):
            await usecase.execute(group_id, directory)

    @pytest.mark.asyncio
    async def test_execute_エピソード保存でエラーが発生した場合_例外が発生すること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        group_id = GroupId("test-group")
        directory = "/docs"

        file_reader = Mock()
        doc_parser = Mock()
        episode_repository = AsyncMock()

        # 正常なファイル処理設定
        file_paths = ["/docs/file1.txt"]
        documents = [Document("/docs/file1.txt", "file1.txt", "txt", "Content 1")]
        elements = [Mock(text="Element 1")]
        chunks = [Chunk("file1_chunk_0", "Chunk 1", {}, documents[0])]

        file_reader.list_supported_files.return_value = file_paths
        file_reader.read_documents.return_value = documents
        doc_parser.parse.return_value = elements
        doc_parser.split_elements.return_value = chunks

        # エピソード保存でエラー
        episode_repository.save_batch.side_effect = Exception("Database error")

        usecase = RegisterDocumentUseCase(
            file_reader=file_reader,
            document_parser=doc_parser,
            episode_repository=episode_repository,
        )

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(Exception, match="Database error"):
            await usecase.execute(group_id, directory)

    @pytest.mark.asyncio
    async def test_execute_複数ファイルの一部で処理エラーが発生した場合_部分的に成功すること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        group_id = GroupId("test-group")
        directory = "/docs"

        file_reader = Mock()
        doc_parser = Mock()
        episode_repository = AsyncMock()

        # ファイル設定
        file_paths = ["/docs/good.txt", "/docs/bad.txt"]
        documents = [
            Document("/docs/good.txt", "good.txt", "txt", "Good content"),
            Document("/docs/bad.txt", "bad.txt", "txt", "Bad content"),
        ]

        file_reader.list_supported_files.return_value = file_paths
        file_reader.read_documents.return_value = documents

        # パースで一部エラー（最初は成功、次はエラー）
        good_elements = [Mock(text="Good element")]
        doc_parser.parse.side_effect = [good_elements, Exception("Parse error")]

        good_chunks = [Chunk("good_chunk_0", "Good chunk", {}, documents[0])]
        doc_parser.split_elements.return_value = good_chunks

        usecase = RegisterDocumentUseCase(
            file_reader=file_reader,
            document_parser=doc_parser,
            episode_repository=episode_repository,
        )

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        result = await usecase.execute(group_id, directory)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # 成功したファイルのみ処理される
        assert doc_parser.parse.call_count == 2
        assert doc_parser.split_elements.call_count == 1  # 成功した1つのみ

        # 成功分のエピソードが保存される
        episode_repository.save_batch.assert_called_once()
        saved_episodes = episode_repository.save_batch.call_args[0][0]
        assert len(saved_episodes) == 1

        # 結果には処理できた分が反映される
        assert result.total_files == 2
        assert result.total_chunks == 1
        assert result.total_episodes == 1
        assert result.success is True  # 部分的成功でもTrue
