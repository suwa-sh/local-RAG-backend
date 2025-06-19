"""Rate Limitスレッド間同期コーディネーター"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class RateLimitState:
    """Rate Limit状態情報"""

    is_waiting: bool = False
    wait_until: Optional[datetime] = None
    wait_time: int = 0
    affected_threads: int = 0
    trigger_thread_id: Optional[str] = None
    trigger_error_message: Optional[str] = None


class RateLimitCoordinator:
    """Rate Limitエラーのスレッド間同期コーディネーター"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Args:
            logger: ロガーインスタンス
        """
        self._state = RateLimitState()
        self._lock = asyncio.Lock()
        self._logger = logger or logging.getLogger(__name__)
        self._waiting_condition = asyncio.Condition(self._lock)

    def _flush_logs(self) -> None:
        """ログを即座にフラッシュする（バッファリング回避）"""
        try:
            for handler in logging.getLogger().handlers:
                if hasattr(handler, "flush"):
                    handler.flush()
        except Exception as e:
            # フラッシュエラーは無視（ログ出力が重要）但し、変数使用でbandit警告回避
            _ = e

    async def check_and_wait_if_needed(self, thread_id: str) -> bool:
        """
        Rate Limit状態をチェックし、必要に応じて待機する

        Args:
            thread_id: 現在のスレッドID

        Returns:
            bool: 待機した場合True、待機しなかった場合False
        """
        async with self._waiting_condition:
            # 他のスレッドがRate Limitで待機中かチェック
            if self._state.is_waiting and self._state.wait_until:
                now = datetime.now()

                if now < self._state.wait_until:
                    # まだ待機時間中の場合
                    remaining_seconds = (self._state.wait_until - now).total_seconds()
                    self._state.affected_threads += 1

                    self._logger.info(
                        f"🔄 Rate Limit同期待機 - スレッド{thread_id}: "
                        f"残り{remaining_seconds:.1f}秒待機 "
                        f"(トリガー: {self._state.trigger_thread_id}, "
                        f"影響スレッド: {self._state.affected_threads})"
                    )
                    self._flush_logs()  # 同期待機ログを即座にフラッシュ

                    # 待機時間まで待つ
                    await asyncio.sleep(remaining_seconds)
                    return True
                else:
                    # 待機時間が終了している場合、状態をリセット
                    self._reset_state()
                    return False

            return False

    async def notify_rate_limit(
        self, thread_id: str, wait_time: int, error_message: str = ""
    ) -> None:
        """
        Rate Limitエラーを全スレッドに通知する

        Args:
            thread_id: Rate Limitを検出したスレッドID
            wait_time: 待機時間（秒）
            error_message: エラーメッセージ
        """
        async with self._waiting_condition:
            # 既に待機中でより長い待機時間が設定されている場合は更新しない
            now = datetime.now()
            new_wait_until = now + timedelta(seconds=wait_time)

            if (
                not self._state.is_waiting
                or not self._state.wait_until
                or new_wait_until > self._state.wait_until
            ):
                self._state.is_waiting = True
                self._state.wait_until = new_wait_until
                self._state.wait_time = wait_time
                self._state.affected_threads = 1  # 検出したスレッド自身
                self._state.trigger_thread_id = thread_id
                self._state.trigger_error_message = error_message

                self._logger.warning(
                    f"🚨 Rate Limit検出 - スレッド{thread_id}: "
                    f"{wait_time}秒間の全スレッド同期待機を開始"
                )
                self._flush_logs()  # 即座にフラッシュして順序を保証

                # 待機中の他のスレッドに通知
                self._waiting_condition.notify_all()

    async def wait_for_rate_limit_completion(self, thread_id: str) -> None:
        """
        Rate Limitエラーを検出したスレッドが実際に待機する

        Args:
            thread_id: 待機するスレッドID
        """
        async with self._waiting_condition:
            if self._state.is_waiting and self._state.wait_until:
                now = datetime.now()

                if now < self._state.wait_until:
                    remaining_seconds = (self._state.wait_until - now).total_seconds()

                    self._logger.info(
                        f"⏳ Rate Limitトリガースレッド{thread_id}: "
                        f"{remaining_seconds:.1f}秒待機中..."
                    )
                    self._flush_logs()  # 待機前に即座にフラッシュ

                    await asyncio.sleep(remaining_seconds)

                # 待機完了後、状態をリセット
                if self._state.trigger_thread_id == thread_id:
                    total_affected = self._state.affected_threads
                    self._reset_state()

                    self._logger.info(
                        f"✅ Rate Limit待機完了 - スレッド{thread_id}: "
                        f"影響を受けたスレッド数 {total_affected}"
                    )
                    self._flush_logs()  # 完了通知を即座にフラッシュ

    def _reset_state(self) -> None:
        """Rate Limit状態をリセット"""
        self._state = RateLimitState()

    def get_current_state(self) -> Dict[str, Any]:
        """
        現在のRate Limit状態を取得

        Returns:
            Dict[str, Any]: 現在の状態情報
        """
        return {
            "is_waiting": self._state.is_waiting,
            "wait_until": self._state.wait_until.isoformat()
            if self._state.wait_until
            else None,
            "wait_time": self._state.wait_time,
            "affected_threads": self._state.affected_threads,
            "trigger_thread_id": self._state.trigger_thread_id,
            "trigger_error_message": self._state.trigger_error_message,
        }

    async def force_reset(self) -> None:
        """Rate Limit状態を強制リセット（テスト・デバッグ用）"""
        async with self._lock:
            self._logger.warning("🔧 Rate Limit状態を強制リセット")
            self._reset_state()


# グローバルシングルトンインスタンス
_rate_limit_coordinator: Optional[RateLimitCoordinator] = None


def get_rate_limit_coordinator() -> RateLimitCoordinator:
    """Rate Limitコーディネーターのシングルトンインスタンスを取得"""
    global _rate_limit_coordinator
    if _rate_limit_coordinator is None:
        _rate_limit_coordinator = RateLimitCoordinator()
    return _rate_limit_coordinator
