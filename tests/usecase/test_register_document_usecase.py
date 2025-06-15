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
