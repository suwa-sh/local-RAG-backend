"""Rate Limitエラーのリトライ処理を管理するハンドラー"""

import logging
import re
from typing import Optional

from graphiti_core.llm_client.errors import RateLimitError


class RateLimitRetryHandler:
    """Rate limitエラーのリトライ処理を管理するハンドラー"""

    def __init__(
        self,
        max_retries: int = 3,
        default_wait_time: int = 121,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Args:
            max_retries: 最大リトライ回数
            default_wait_time: デフォルトの待機時間（秒）
            logger: ロガーインスタンス
        """
        self.max_retries = max_retries
        self.default_wait_time = default_wait_time
        self.logger = logger or logging.getLogger(__name__)

    def extract_retry_after_time(self, error: RateLimitError) -> Optional[int]:
        """graphitiのRateLimitErrorから待機時間を抽出

        Args:
            error: RateLimitError

        Returns:
            待機時間（秒）。取得できない場合はNone
        """
        wait_times = []

        # __cause__から元のエラーを取得
        original_error = error.__cause__

        if (
            original_error
            and hasattr(original_error, "response")
            and original_error.response
        ):
            headers = original_error.response.headers

            # retry-afterヘッダー（秒単位）
            if retry_after := headers.get("retry-after"):
                try:
                    wait_times.append(int(float(retry_after)))
                except (ValueError, TypeError):
                    pass

            # x-ratelimit-reset-tokens（例: "1m1.398s"）をパース
            if reset_tokens := headers.get("x-ratelimit-reset-tokens"):
                if parsed_time := self._parse_time_string(reset_tokens):
                    wait_times.append(parsed_time)

        # 最も長い待機時間を採用 + 1秒のバッファ
        if wait_times:
            return max(wait_times) + 1

        return None

    def _parse_time_string(self, time_str: str) -> Optional[int]:
        """時間文字列（例: "1m1.398s"）を秒数に変換

        Args:
            time_str: 時間文字列

        Returns:
            秒数。パースできない場合はNone
        """
        total_seconds = 0

        # 分を検索
        if match := re.search(r"(\d+)m", time_str):
            total_seconds += int(match.group(1)) * 60

        # 秒を検索
        if match := re.search(r"(\d+(?:\.\d+)?)s", time_str):
            total_seconds += int(float(match.group(1)))

        return total_seconds if total_seconds > 0 else None
