"""エンティティキャッシュのテスト"""

from datetime import datetime

from src.adapter.entity_cache import (
    FileBasedEntityCache,
    EntityCacheEntry,
    get_entity_cache,
)


class TestEntityCacheEntry:
    """EntityCacheEntryのテスト"""

    def test_EntityCacheEntry作成_正常な値を指定した場合_インスタンスが作成されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        name = "test_entity"
        entity_type = "PERSON"
        summary = "Test entity summary"
        attributes = {"key": "value"}
        created_at = datetime.now()

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        entry = EntityCacheEntry(
            name=name,
            entity_type=entity_type,
            summary=summary,
            attributes=attributes,
            created_at=created_at,
        )

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert entry.name == name
        assert entry.entity_type == entity_type
        assert entry.summary == summary
        assert entry.attributes == attributes
        assert entry.created_at == created_at
        assert entry.hit_count == 0


class TestFileBasedEntityCache:
    """FileBasedEntityCacheのテスト"""

    def test_FileBasedEntityCache初期化_インスタンスが作成されること(self):
        # ------------------------------
        # 準備 (Arrange) & 実行 (Act)
        # ------------------------------
        cache = FileBasedEntityCache()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert cache._cache == {}
        assert cache._stats["cache_hits"] == 0
        assert cache._stats["cache_misses"] == 0
        assert cache._stats["total_entities_cached"] == 0

    def test_cache_entity_新規エンティティをキャッシュした場合_正常に保存されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        cache = FileBasedEntityCache()
        file_path = "/test/file.txt"
        entity_name = "TestEntity"
        entity_type = "PERSON"
        summary = "Test summary"
        attributes = {"key": "value"}

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        cache.cache_entity(file_path, entity_name, entity_type, summary, attributes)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert file_path in cache._cache
        assert entity_name.lower() in cache._cache[file_path]

        entry = cache._cache[file_path][entity_name.lower()]
        assert entry.name == entity_name
        assert entry.entity_type == entity_type
        assert entry.summary == summary
        assert entry.attributes == attributes
        assert cache._stats["total_entities_cached"] == 1

    def test_cache_entity_既存エンティティを更新した場合_正常に更新されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        cache = FileBasedEntityCache()
        file_path = "/test/file.txt"
        entity_name = "TestEntity"
        entity_type = "PERSON"

        # 最初のキャッシュ
        cache.cache_entity(
            file_path, entity_name, entity_type, "Old summary", {"old": "value"}
        )

        new_summary = "New summary"
        new_attributes = {"new": "value"}

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        cache.cache_entity(
            file_path, entity_name, entity_type, new_summary, new_attributes
        )

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        entry = cache._cache[file_path][entity_name.lower()]
        assert entry.summary == new_summary
        assert entry.attributes == new_attributes
        # カウントは増えない（更新のため）
        assert cache._stats["total_entities_cached"] == 1

    def test_get_entity_キャッシュに存在するエンティティを取得した場合_適切なエントリが返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        cache = FileBasedEntityCache()
        file_path = "/test/file.txt"
        entity_name = "TestEntity"
        entity_type = "PERSON"
        summary = "Test summary"
        attributes = {"key": "value"}

        cache.cache_entity(file_path, entity_name, entity_type, summary, attributes)

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        result = cache.get_entity(file_path, entity_name)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert result is not None
        assert result.name == entity_name
        assert result.entity_type == entity_type
        assert result.summary == summary
        assert result.attributes == attributes
        assert result.hit_count == 1
        assert cache._stats["cache_hits"] == 1
        assert cache._stats["cache_misses"] == 0

    def test_get_entity_キャッシュに存在しないエンティティを取得した場合_Noneが返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        cache = FileBasedEntityCache()
        file_path = "/test/file.txt"
        entity_name = "NonExistentEntity"

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        result = cache.get_entity(file_path, entity_name)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert result is None
        assert cache._stats["cache_hits"] == 0
        assert cache._stats["cache_misses"] == 1

    def test_has_entity_キャッシュに存在するエンティティをチェックした場合_Trueが返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        cache = FileBasedEntityCache()
        file_path = "/test/file.txt"
        entity_name = "TestEntity"

        cache.cache_entity(file_path, entity_name, "PERSON", "summary")

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        result = cache.has_entity(file_path, entity_name)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert result is True

    def test_has_entity_キャッシュに存在しないエンティティをチェックした場合_Falseが返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        cache = FileBasedEntityCache()
        file_path = "/test/file.txt"
        entity_name = "NonExistentEntity"

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        result = cache.has_entity(file_path, entity_name)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert result is False

    def test_get_file_entities_ファイル内の全エンティティを取得した場合_適切な辞書が返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        cache = FileBasedEntityCache()
        file_path = "/test/file.txt"

        cache.cache_entity(file_path, "Entity1", "PERSON", "summary1")
        cache.cache_entity(file_path, "Entity2", "ORGANIZATION", "summary2")

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        result = cache.get_file_entities(file_path)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert len(result) == 2
        assert "entity1" in result
        assert "entity2" in result
        assert result["entity1"].name == "Entity1"
        assert result["entity2"].name == "Entity2"

    def test_clear_file_cache_特定ファイルのキャッシュをクリアした場合_そのファイルのキャッシュが削除されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        cache = FileBasedEntityCache()
        file_path1 = "/test/file1.txt"
        file_path2 = "/test/file2.txt"

        cache.cache_entity(file_path1, "Entity1", "PERSON", "summary1")
        cache.cache_entity(file_path2, "Entity2", "ORGANIZATION", "summary2")

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        cache.clear_file_cache(file_path1)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert file_path1 not in cache._cache
        assert file_path2 in cache._cache
        assert len(cache._cache[file_path2]) == 1

    def test_clear_all_cache_全キャッシュをクリアした場合_すべてのキャッシュが削除されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        cache = FileBasedEntityCache()
        file_path1 = "/test/file1.txt"
        file_path2 = "/test/file2.txt"

        cache.cache_entity(file_path1, "Entity1", "PERSON", "summary1")
        cache.cache_entity(file_path2, "Entity2", "ORGANIZATION", "summary2")

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        cache.clear_all_cache()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert cache._cache == {}
        assert cache._stats["cache_hits"] == 0
        assert cache._stats["cache_misses"] == 0
        assert cache._stats["total_entities_cached"] == 0

    def test_get_cache_stats_キャッシュ統計を取得した場合_適切な統計が返されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        cache = FileBasedEntityCache()
        file_path = "/test/file.txt"

        # キャッシュの作成とアクセス
        cache.cache_entity(file_path, "Entity1", "PERSON", "summary1")
        cache.cache_entity(file_path, "Entity2", "ORGANIZATION", "summary2")
        cache.get_entity(file_path, "Entity1")  # ヒット
        cache.get_entity(file_path, "NonExistent")  # ミス

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        stats = cache.get_cache_stats()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert abs(stats["hit_rate_percentage"] - 50.0) < 0.01
        assert stats["total_entities_cached"] == 2
        assert stats["total_files_cached"] == 1
        assert abs(stats["average_entities_per_file"] - 2.0) < 0.01


class TestGetEntityCache:
    """get_entity_cache関数のテスト"""

    def test_get_entity_cache_シングルトンインスタンスが返されること(self):
        # ------------------------------
        # 準備 (Arrange) & 実行 (Act)
        # ------------------------------
        cache1 = get_entity_cache()
        cache2 = get_entity_cache()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert cache1 is cache2
        assert isinstance(cache1, FileBasedEntityCache)
