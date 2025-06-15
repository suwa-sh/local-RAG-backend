"""RateLimitRetryHandlerのテスト"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Optional

from src.adapter.rate_limit_retry_handler import RateLimitRetryHandler


class TestRateLimitRetryHandler:
    """RateLimitRetryHandlerのテストクラス"""

    @pytest.fixture
    def handler(self):
        """テスト用のハンドラーインスタンス"""
        return RateLimitRetryHandler()

    def test_extract_retry_after_time_retry_afterヘッダーがある場合_秒数を返すこと(
        self, handler
    ):
        """retry-afterヘッダーから待機時間を抽出できることを確認"""
        # 準備 (Arrange)
        mock_response = Mock()
        mock_response.headers = {"retry-after": "5"}

        mock_original_error = Mock()
        mock_original_error.response = mock_response

        mock_rate_limit_error = Mock()
        mock_rate_limit_error.__cause__ = mock_original_error

        # 実行 (Act)
        result = handler.extract_retry_after_time(mock_rate_limit_error)

        # 検証 (Assert)
        assert result == 6  # 5秒 + 1秒のバッファ

    def test_extract_retry_after_time_x_ratelimit_reset_tokensヘッダーがある場合_秒数を返すこと(
        self, handler
    ):
        """x-ratelimit-reset-tokensヘッダーから待機時間を抽出できることを確認"""
        # 準備 (Arrange)
        mock_response = Mock()
        mock_response.headers = {"x-ratelimit-reset-tokens": "1m30.5s"}

        mock_original_error = Mock()
        mock_original_error.response = mock_response

        mock_rate_limit_error = Mock()
        mock_rate_limit_error.__cause__ = mock_original_error

        # 実行 (Act)
        result = handler.extract_retry_after_time(mock_rate_limit_error)

        # 検証 (Assert)
        assert result == 91  # 90.5秒 → 90秒 + 1秒のバッファ

    def test_extract_retry_after_time_両方のヘッダーがある場合_長い方を返すこと(
        self, handler
    ):
        """両方のヘッダーがある場合、より長い待機時間を返すことを確認"""
        # 準備 (Arrange)
        mock_response = Mock()
        mock_response.headers = {
            "retry-after": "5",
            "x-ratelimit-reset-tokens": "2m10s",
        }

        mock_original_error = Mock()
        mock_original_error.response = mock_response

        mock_rate_limit_error = Mock()
        mock_rate_limit_error.__cause__ = mock_original_error

        # 実行 (Act)
        result = handler.extract_retry_after_time(mock_rate_limit_error)

        # 検証 (Assert)
        assert result == 131  # 130秒 + 1秒のバッファ（5秒より長い）

    def test_extract_retry_after_time_ヘッダーがない場合_Noneを返すこと(self, handler):
        """ヘッダーがない場合、Noneを返すことを確認"""
        # 準備 (Arrange)
        mock_response = Mock()
        mock_response.headers = {}

        mock_original_error = Mock()
        mock_original_error.response = mock_response

        mock_rate_limit_error = Mock()
        mock_rate_limit_error.__cause__ = mock_original_error

        # 実行 (Act)
        result = handler.extract_retry_after_time(mock_rate_limit_error)

        # 検証 (Assert)
        assert result is None

    def test_extract_retry_after_time_causeがない場合_Noneを返すこと(self, handler):
        """__cause__がない場合、Noneを返すことを確認"""
        # 準備 (Arrange)
        mock_rate_limit_error = Mock()
        mock_rate_limit_error.__cause__ = None

        # 実行 (Act)
        result = handler.extract_retry_after_time(mock_rate_limit_error)

        # 検証 (Assert)
        assert result is None

    def test_parse_time_string_分と秒の組み合わせ_正しく変換されること(self, handler):
        """時間文字列のパースが正しく動作することを確認"""
        # 準備 (Arrange)
        test_cases = [
            ("1m30s", 90),
            ("2m", 120),
            ("45.5s", 45),
            ("1m1.398s", 61),  # 実際のログから
            ("0m10s", 10),
        ]

        # 実行・検証 (Act & Assert)
        for time_str, expected in test_cases:
            result = handler._parse_time_string(time_str)
            assert result == expected, f"Failed for {time_str}"

    def test_parse_time_string_無効な文字列_Noneを返すこと(self, handler):
        """無効な時間文字列の場合、Noneを返すことを確認"""
        # 準備 (Arrange)
        test_cases = ["invalid", "", "abc", "123"]

        # 実行・検証 (Act & Assert)
        for time_str in test_cases:
            result = handler._parse_time_string(time_str)
            assert result is None, f"Failed for {time_str}"

    def test_is_rate_limit_error_RateLimitErrorの場合_Trueを返すこと(self, handler):
        """RateLimitErrorを正しく判定できることを確認"""
        # 準備 (Arrange)
        from graphiti_core.llm_client.errors import RateLimitError

        error = RateLimitError("Rate limit exceeded")

        # 実行 (Act)
        result = handler.is_rate_limit_error(error)

        # 検証 (Assert)
        assert result is True

    def test_is_rate_limit_error_他のエラーの場合_Falseを返すこと(self, handler):
        """他のエラーの場合、Falseを返すことを確認"""
        # 準備 (Arrange)
        error = ValueError("Some other error")

        # 実行 (Act)
        result = handler.is_rate_limit_error(error)

        # 検証 (Assert)
        assert result is False
