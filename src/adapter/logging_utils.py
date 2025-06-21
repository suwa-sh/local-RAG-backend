"""ロギングユーティリティ - スレッド別・ファイル別のコンテキスト管理"""

import logging
import threading
from contextvars import ContextVar
from typing import Optional, Any


# コンテキスト変数：現在処理中のファイル名を保持
current_file: ContextVar[Optional[str]] = ContextVar("current_file", default=None)


class FileContextFilter(logging.Filter):
    """ファイルコンテキストをログレコードに追加するフィルター"""

    def filter(self, record: logging.LogRecord) -> bool:
        """
        ログレコードにファイル情報を追加する

        Args:
            record: ログレコード

        Returns:
            bool: 常にTrue（フィルタリングはしない）
        """
        # 現在のファイル名を取得
        file_name = current_file.get()

        # 常にコンテキスト情報を設定（空でもプレースホルダーを表示）
        if file_name:
            # ファイル名から拡張子を除いた短い名前を作成
            short_name = file_name.split("/")[-1].split(".")[0][:20]
            record.file_context = f"[{short_name}]"
        else:
            record.file_context = "[--------]"

        # スレッドIDは常に表示
        thread_id = threading.current_thread().ident
        if thread_id:
            record.thread_name = f"[T{thread_id % 1000:03d}]"
        else:
            record.thread_name = "[T---]"

        return True


def setup_parallel_logging(log_level: str = "INFO") -> None:
    """
    並列処理用のログ設定を初期化する

    Args:
        log_level: ログレベル（DEBUG, INFO, WARNING, ERROR）
    """
    # ルートロガーを取得
    root_logger = logging.getLogger()

    # 既存のハンドラーをクリア
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 新しいハンドラーを作成
    handler = logging.StreamHandler()

    # ファイルコンテキストフィルターを追加
    handler.addFilter(FileContextFilter())

    # フォーマッターを設定（ファイル名とスレッドIDを含む）
    formatter = logging.Formatter(
        "%(asctime)s %(thread_name)s%(file_context)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)

    # ハンドラーを追加
    root_logger.addHandler(handler)

    # 環境変数で指定されたログレベルを設定
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
