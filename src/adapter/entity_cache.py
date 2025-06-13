"""エンティティキャッシュ - 同一ファイル内キャッシュ実装"""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class EntityCacheEntry:
    """エンティティキャッシュエントリ"""

    name: str
    entity_type: str
    summary: str
    attributes: Dict[str, Any]
    created_at: datetime
    hit_count: int = 0


class FileBasedEntityCache:
    """ファイル内エンティティキャッシュ"""

    def __init__(self):
        """キャッシュ初期化"""
        self._cache: Dict[str, Dict[str, EntityCacheEntry]] = {}
        self._logger = logging.getLogger(__name__)
        self._stats = {"cache_hits": 0, "cache_misses": 0, "total_entities_cached": 0}

    def get_entity(
        self, file_path: str, entity_name: str
    ) -> Optional[EntityCacheEntry]:
        """
        ファイル内エンティティキャッシュから取得

        Args:
            file_path: ファイルパス
            entity_name: エンティティ名

        Returns:
            EntityCacheEntry: キャッシュエントリ（見つからない場合はNone）
        """
        normalized_name = entity_name.lower().strip()

        file_entities = self._cache.get(file_path, {})
        cache_entry = file_entities.get(normalized_name)

        if cache_entry:
            cache_entry.hit_count += 1
            self._stats["cache_hits"] += 1
            self._logger.debug(f"🎯 キャッシュヒット: {entity_name} in {file_path}")
            return cache_entry
        else:
            self._stats["cache_misses"] += 1
            self._logger.debug(f"❌ キャッシュミス: {entity_name} in {file_path}")
            return None

    def cache_entity(
        self,
        file_path: str,
        entity_name: str,
        entity_type: str,
        summary: str,
        attributes: Dict[str, Any] = None,
    ) -> None:
        """
        エンティティをファイル内キャッシュに保存

        Args:
            file_path: ファイルパス
            entity_name: エンティティ名
            entity_type: エンティティタイプ
            summary: エンティティ要約
            attributes: 追加属性
        """
        if file_path not in self._cache:
            self._cache[file_path] = {}

        normalized_name = entity_name.lower().strip()

        # 既存エントリがある場合は更新
        if normalized_name in self._cache[file_path]:
            existing_entry = self._cache[file_path][normalized_name]
            existing_entry.summary = summary  # 要約を最新に更新
            existing_entry.attributes = attributes or {}
            self._logger.debug(f"🔄 キャッシュ更新: {entity_name} in {file_path}")
        else:
            # 新規エントリ作成
            cache_entry = EntityCacheEntry(
                name=entity_name,
                entity_type=entity_type,
                summary=summary,
                attributes=attributes or {},
                created_at=datetime.now(),
            )

            self._cache[file_path][normalized_name] = cache_entry
            self._stats["total_entities_cached"] += 1
            self._logger.debug(f"💾 キャッシュ新規登録: {entity_name} in {file_path}")

    def has_entity(self, file_path: str, entity_name: str) -> bool:
        """
        エンティティがキャッシュに存在するかチェック

        Args:
            file_path: ファイルパス
            entity_name: エンティティ名

        Returns:
            bool: 存在する場合True
        """
        normalized_name = entity_name.lower().strip()
        file_entities = self._cache.get(file_path, {})
        return normalized_name in file_entities

    def get_file_entities(self, file_path: str) -> Dict[str, EntityCacheEntry]:
        """
        ファイル内の全エンティティを取得

        Args:
            file_path: ファイルパス

        Returns:
            Dict[str, EntityCacheEntry]: ファイル内のエンティティ一覧
        """
        return self._cache.get(file_path, {}).copy()

    def clear_file_cache(self, file_path: str) -> None:
        """
        特定ファイルのキャッシュをクリア

        Args:
            file_path: クリア対象のファイルパス
        """
        if file_path in self._cache:
            entity_count = len(self._cache[file_path])
            del self._cache[file_path]
            self._logger.info(
                f"🧹 ファイルキャッシュクリア: {file_path} ({entity_count}エンティティ)"
            )

    def clear_all_cache(self) -> None:
        """全キャッシュをクリア"""
        total_entities = sum(len(entities) for entities in self._cache.values())
        self._cache.clear()
        self._stats = {"cache_hits": 0, "cache_misses": 0, "total_entities_cached": 0}
        self._logger.info(f"🧹 全キャッシュクリア ({total_entities}エンティティ)")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        キャッシュ統計情報を取得

        Returns:
            Dict[str, Any]: キャッシュ統計
        """
        total_requests = self._stats["cache_hits"] + self._stats["cache_misses"]
        hit_rate = (
            (self._stats["cache_hits"] / total_requests * 100)
            if total_requests > 0
            else 0
        )

        return {
            "cache_hits": self._stats["cache_hits"],
            "cache_misses": self._stats["cache_misses"],
            "hit_rate_percentage": round(hit_rate, 2),
            "total_entities_cached": self._stats["total_entities_cached"],
            "total_files_cached": len(self._cache),
            "average_entities_per_file": (
                round(self._stats["total_entities_cached"] / len(self._cache), 2)
                if self._cache
                else 0
            ),
        }

    def log_cache_stats(self) -> None:
        """キャッシュ統計をログ出力"""
        stats = self.get_cache_stats()
        self._logger.info(
            f"📊 キャッシュ統計: "
            f"ヒット率 {stats['hit_rate_percentage']}% "
            f"({stats['cache_hits']}/{stats['cache_hits'] + stats['cache_misses']}) | "
            f"キャッシュエンティティ数 {stats['total_entities_cached']} | "
            f"対象ファイル数 {stats['total_files_cached']}"
        )


# シングルトンインスタンス
_entity_cache_instance: Optional[FileBasedEntityCache] = None


def get_entity_cache() -> FileBasedEntityCache:
    """エンティティキャッシュのシングルトンインスタンスを取得"""
    global _entity_cache_instance
    if _entity_cache_instance is None:
        _entity_cache_instance = FileBasedEntityCache()
    return _entity_cache_instance
