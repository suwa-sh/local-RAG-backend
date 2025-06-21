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

    def log_cache_stats(self) -> None:
        """キャッシュ統計をログ出力"""
        # 簡単なログ出力のみで統計取得は廃止
        total_files = len(self._cache)
        total_entities = sum(len(entities) for entities in self._cache.values())
        self._logger.info(
            f"📊 キャッシュ統計: "
            f"キャッシュエンティティ数 {total_entities} | "
            f"対象ファイル数 {total_files}"
        )


# シングルトンインスタンス
_entity_cache_instance: Optional[FileBasedEntityCache] = None


def get_entity_cache() -> FileBasedEntityCache:
    """エンティティキャッシュのシングルトンインスタンスを取得"""
    global _entity_cache_instance
    if _entity_cache_instance is None:
        _entity_cache_instance = FileBasedEntityCache()
    return _entity_cache_instance
