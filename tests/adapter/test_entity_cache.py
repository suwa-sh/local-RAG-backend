"""エンティティキャッシュのテスト"""

import pytest
import tempfile
import shutil

from src.adapter.entity_cache import (
    FileBasedEntityCache,
    get_entity_cache,
)


@pytest.fixture
def temp_dir():
    """一時ディレクトリを作成"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestFileBasedEntityCache:
    """FileBasedEntityCacheのテスト"""

    def test_log_cache_stats_基本動作確認(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        cache = FileBasedEntityCache()

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        cache.log_cache_stats()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # log_cache_statsはログ出力のみでNoneを返すため、エラーが発生しないことを確認
        # メソッドが正常に実行されることを確認（例外が発生しないことをテスト）

    # 削除されたメソッドに依存するテストをコメントアウト
    # 未使用メソッド削除により以下のメソッドは利用不可:
    # cache_entity, get_entity, has_entity, get_file_entities, clear_file_cache, clear_all_cache, get_cache_stats

    def test_削除されたメソッドに依存するテスト_スキップ(self):
        """削除されたメソッドに依存するテストはスキップ"""
        pass


class TestGetEntityCache:
    """get_entity_cache関数のテスト"""

    def test_get_entity_cache_基本動作確認(self):
        # ------------------------------
        # 準備 (Arrange) & 実行 (Act)
        # ------------------------------
        cache = get_entity_cache()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert isinstance(cache, FileBasedEntityCache), (
            "FileBasedEntityCacheのインスタンスが返される必要があります"
        )
