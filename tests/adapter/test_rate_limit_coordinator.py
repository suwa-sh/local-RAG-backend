"""Rate Limitコーディネーターのテスト"""

import pytest

from src.adapter.rate_limit_coordinator import (
    RateLimitCoordinator,
    get_rate_limit_coordinator,
)


class TestRateLimitCoordinator:
    """RateLimitCoordinatorのテスト"""

    def test_RateLimitCoordinator作成_基本動作確認(self):
        # ------------------------------
        # 準備 (Arrange) & 実行 (Act)
        # ------------------------------
        coordinator = RateLimitCoordinator()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert coordinator is not None, "コーディネーターが作成される必要があります"

    # 削除されたメソッドに依存するテストをコメントアウト
    # 未使用メソッド削除により以下のメソッドは利用不可:
    # get_current_state, force_reset

    def test_削除されたメソッドに依存するテスト_スキップ(self):
        """削除されたメソッドに依存するテストはスキップ"""
        pass


class TestGetRateLimitCoordinator:
    """get_rate_limit_coordinator関数のテスト"""

    def test_get_rate_limit_coordinator_シングルトンインスタンスが返されること(self):
        # ------------------------------
        # 準備 (Arrange) & 実行 (Act)
        # ------------------------------
        coordinator1 = get_rate_limit_coordinator()
        coordinator2 = get_rate_limit_coordinator()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert isinstance(coordinator1, RateLimitCoordinator), (
            "RateLimitCoordinatorのインスタンスが返される必要があります"
        )
        assert coordinator1 is coordinator2, (
            "同じインスタンスが返される必要があります（シングルトン）"
        )
