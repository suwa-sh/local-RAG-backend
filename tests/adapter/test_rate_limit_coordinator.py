"""Rate Limitコーディネーターのテスト"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.adapter.rate_limit_coordinator import (
    RateLimitCoordinator,
    RateLimitState,
    get_rate_limit_coordinator,
)


class TestRateLimitState:
    """RateLimitStateのテスト"""

    def test_RateLimitState作成_デフォルト値が設定されること(self):
        # ------------------------------
        # 準備 (Arrange) & 実行 (Act)
        # ------------------------------
        state = RateLimitState()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert state.is_waiting is False
        assert state.wait_until is None
        assert state.wait_time == 0
        assert state.affected_threads == 0
        assert state.trigger_thread_id is None
        assert state.trigger_error_message is None


class TestRateLimitCoordinator:
    """RateLimitCoordinatorのテスト"""

    def test_RateLimitCoordinator初期化_インスタンスが作成されること(self):
        # ------------------------------
        # 準備 (Arrange) & 実行 (Act)
        # ------------------------------
        coordinator = RateLimitCoordinator()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert coordinator is not None
        assert coordinator._state.is_waiting is False

    @pytest.mark.asyncio
    async def test_check_and_wait_if_needed_Rate_Limit状態でない場合_待機しないこと(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        coordinator = RateLimitCoordinator()
        thread_id = "thread_1"

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        result = await coordinator.check_and_wait_if_needed(thread_id)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert result is False

    @pytest.mark.asyncio
    async def test_notify_rate_limit_Rate_Limitを通知した場合_状態が更新されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        coordinator = RateLimitCoordinator()
        thread_id = "thread_1"
        wait_time = 60
        error_message = "Rate limit exceeded"

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        await coordinator.notify_rate_limit(thread_id, wait_time, error_message)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        state = coordinator.get_current_state()
        assert state["is_waiting"] is True
        assert state["wait_time"] == wait_time
        assert state["affected_threads"] == 1
        assert state["trigger_thread_id"] == thread_id
        assert state["trigger_error_message"] == error_message

    @pytest.mark.asyncio
    async def test_check_and_wait_if_needed_Rate_Limit状態の場合_待機すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        coordinator = RateLimitCoordinator()
        trigger_thread = "thread_1"
        waiting_thread = "thread_2"
        wait_time = 1  # 短い待機時間

        # Rate Limit状態を設定
        await coordinator.notify_rate_limit(trigger_thread, wait_time)

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch("asyncio.sleep") as mock_sleep:
            result = await coordinator.check_and_wait_if_needed(waiting_thread)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert result is True
        # 実際の残り時間で待機が呼ばれる
        assert mock_sleep.call_count == 1
        # 待機時間は1秒以下（残り時間）
        assert 0 <= mock_sleep.call_args[0][0] <= 1.1

    @pytest.mark.asyncio
    async def test_wait_for_rate_limit_completion_Rate_Limitトリガースレッドが待機完了すること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        coordinator = RateLimitCoordinator()
        thread_id = "thread_1"
        wait_time = 1  # 短い待機時間

        # Rate Limit状態を設定
        await coordinator.notify_rate_limit(thread_id, wait_time)

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch("asyncio.sleep") as mock_sleep:
            await coordinator.wait_for_rate_limit_completion(thread_id)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # 実際の残り時間で待機が呼ばれる
        assert mock_sleep.call_count == 1
        # 状態がリセットされる
        state = coordinator.get_current_state()
        assert state["is_waiting"] is False

    @pytest.mark.asyncio
    async def test_notify_rate_limit_より長い待機時間が設定済みの場合_更新されないこと(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        coordinator = RateLimitCoordinator()
        thread1 = "thread_1"
        thread2 = "thread_2"

        # より長い待機時間を最初に設定
        await coordinator.notify_rate_limit(thread1, 120)  # 2分
        coordinator.get_current_state()

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        # より短い待機時間で通知
        await coordinator.notify_rate_limit(thread2, 60)  # 1分

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        final_state = coordinator.get_current_state()
        assert final_state["wait_time"] == 120  # 最初の長い待機時間が保持される
        assert (
            final_state["trigger_thread_id"] == thread1
        )  # 最初のスレッドIDが保持される

    @pytest.mark.asyncio
    async def test_notify_rate_limit_より短い待機時間が設定済みの場合_更新されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        coordinator = RateLimitCoordinator()
        thread1 = "thread_1"
        thread2 = "thread_2"

        # より短い待機時間を最初に設定
        await coordinator.notify_rate_limit(thread1, 60)  # 1分

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        # より長い待機時間で通知
        await coordinator.notify_rate_limit(thread2, 120)  # 2分

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        state = coordinator.get_current_state()
        assert state["wait_time"] == 120  # 長い待機時間に更新される
        assert state["trigger_thread_id"] == thread2  # 新しいスレッドIDに更新される

    @pytest.mark.asyncio
    async def test_check_and_wait_if_needed_待機時間が終了済みの場合_待機しないこと(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        coordinator = RateLimitCoordinator()
        thread_id = "thread_1"

        # 既に終了した待機時間を設定
        coordinator._state.is_waiting = True
        coordinator._state.wait_until = datetime.now() - timedelta(seconds=10)

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        result = await coordinator.check_and_wait_if_needed(thread_id)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert result is False
        # 状態がリセットされる
        assert coordinator._state.is_waiting is False

    @pytest.mark.asyncio
    async def test_force_reset_状態が強制リセットされること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        coordinator = RateLimitCoordinator()

        # Rate Limit状態を設定
        await coordinator.notify_rate_limit("thread_1", 60)
        assert coordinator._state.is_waiting is True

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        await coordinator.force_reset()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert coordinator._state.is_waiting is False
        state = coordinator.get_current_state()
        assert state["is_waiting"] is False


class TestGetRateLimitCoordinator:
    """get_rate_limit_coordinatorのテスト"""

    def test_get_rate_limit_coordinator_シングルトンインスタンスが返されること(self):
        # ------------------------------
        # 準備 (Arrange) & 実行 (Act)
        # ------------------------------
        coordinator1 = get_rate_limit_coordinator()
        coordinator2 = get_rate_limit_coordinator()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert coordinator1 is coordinator2  # 同じインスタンス
        assert isinstance(coordinator1, RateLimitCoordinator)

    def test_get_rate_limit_coordinator_初回呼び出しでインスタンスが作成されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        # グローバル変数をクリア（テスト用）
        import src.adapter.rate_limit_coordinator

        src.adapter.rate_limit_coordinator._rate_limit_coordinator = None

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        coordinator = get_rate_limit_coordinator()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert coordinator is not None
        assert isinstance(coordinator, RateLimitCoordinator)
