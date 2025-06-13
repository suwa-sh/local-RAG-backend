"""ingest.pyのテスト"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys

from src.main.ingest import main, create_usecase, parse_arguments


class TestIngest:
    """ingest.pyのテストクラス"""

    def test_parse_arguments_正常な引数を指定した場合_適切にパースされること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        test_args = ["ingest.py", "test-group", "/docs/test"]

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch.object(sys, "argv", test_args):
            args = parse_arguments()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert args.group_id == "test-group"
        assert args.directory == "/docs/test"

    def test_parse_arguments_引数が不足している場合_適切なエラーメッセージが表示されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        test_args = ["ingest.py", "test-group"]  # directoryが不足

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit):
                parse_arguments()

    def test_create_usecase_適切なユースケースインスタンスが作成されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        env_vars = {
            "NEO4J_URL": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password",
            "LLM_MODEL_URL": "http://localhost:4000/v1",
            "LLM_MODEL_NAME": "claude-sonnet-4",
            "LLM_MODEL_KEY": "sk-1234",
            "RERANK_MODEL_NAME": "gpt-4.1-nano",
            "EMBEDDING_MODEL_URL": "http://localhost:11434/v1",
            "EMBEDDING_MODEL_NAME": "kun432/cl-nagoya-ruri-large:latest",
            "EMBEDDING_MODEL_KEY": "dummy",
        }

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch.dict("os.environ", env_vars, clear=True):
            with patch("src.main.ingest.GraphitiEpisodeRepository") as mock_repo:
                mock_repo.return_value = Mock()
                usecase = create_usecase()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert usecase is not None
        assert hasattr(usecase, "execute_parallel")
        assert hasattr(usecase, "_file_reader")
        assert hasattr(usecase, "_document_parser")
        assert hasattr(usecase, "_episode_repository")

    @pytest.mark.asyncio
    async def test_main_正常な引数で実行した場合_成功メッセージが表示されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        test_args = ["ingest.py", "test-group", "/docs/test"]

        # ユースケースのモック
        mock_usecase = AsyncMock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.total_files = 5
        mock_result.total_chunks = 12
        mock_result.total_episodes = 12
        mock_usecase.execute_parallel.return_value = mock_result

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch.object(sys, "argv", test_args):
            with patch("src.main.ingest.create_usecase") as mock_create:
                mock_create.return_value = mock_usecase
                with patch("builtins.print") as mock_print:
                    await main()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # ユースケースが正しく呼ばれたこと
        mock_create.assert_called_once()
        mock_usecase.execute_parallel.assert_called_once()

        # 実行結果の確認
        call_args = mock_usecase.execute_parallel.call_args
        assert call_args[0][0].value == "test-group"  # GroupId
        assert call_args[0][1] == "/docs/test"  # directory
        assert call_args[1]["max_workers"] == 3  # max_workers (デフォルト値)

        # 成功メッセージが出力されたこと
        mock_print.assert_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        success_message_found = any(
            "正常に登録されました" in call for call in print_calls
        )
        assert success_message_found

    @pytest.mark.asyncio
    async def test_main_ディレクトリが存在しない場合_エラーメッセージが表示されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        test_args = ["ingest.py", "test-group", "/nonexistent"]

        mock_usecase = AsyncMock()
        mock_usecase.execute_parallel.side_effect = FileNotFoundError(
            "Directory not found"
        )

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch.object(sys, "argv", test_args):
            with patch("src.main.ingest.create_usecase") as mock_create:
                mock_create.return_value = mock_usecase
                with patch("builtins.print") as mock_print:
                    exit_code = await main()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # エラーメッセージが出力されたこと
        mock_print.assert_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        error_message_found = any("エラー" in call for call in print_calls)
        assert error_message_found

        # 終了コードが1であること
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_main_データベースエラーが発生した場合_エラーメッセージが表示されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        test_args = ["ingest.py", "test-group", "/docs/test"]

        mock_usecase = AsyncMock()
        mock_usecase.execute_parallel.side_effect = Exception(
            "Database connection failed"
        )

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch.object(sys, "argv", test_args):
            with patch("src.main.ingest.create_usecase") as mock_create:
                mock_create.return_value = mock_usecase
                with patch("builtins.print") as mock_print:
                    exit_code = await main()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # エラーメッセージが出力されたこと
        mock_print.assert_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        error_message_found = any("予期しないエラー" in call for call in print_calls)
        assert error_message_found

        # 終了コードが1であること
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_main_空のディレクトリの場合_適切なメッセージが表示されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        test_args = ["ingest.py", "test-group", "/empty"]

        mock_usecase = AsyncMock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.total_files = 0
        mock_result.total_chunks = 0
        mock_result.total_episodes = 0
        mock_usecase.execute_parallel.return_value = mock_result

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch.object(sys, "argv", test_args):
            with patch("src.main.ingest.create_usecase") as mock_create:
                mock_create.return_value = mock_usecase
                with patch("builtins.print") as mock_print:
                    await main()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # 適切なメッセージが出力されたこと
        mock_print.assert_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        no_files_message_found = any(
            "処理対象のファイルがありませんでした" in call for call in print_calls
        )
        assert no_files_message_found

    @pytest.mark.asyncio
    async def test_main_環境変数が不足している場合_設定エラーメッセージが表示されること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        test_args = ["ingest.py", "test-group", "/docs/test"]

        # 環境変数を空にする
        env_vars = {}

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        with patch.object(sys, "argv", test_args):
            with patch.dict("os.environ", env_vars, clear=True):
                with patch("builtins.print") as mock_print:
                    exit_code = await main()

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        # 設定エラーメッセージが出力されたこと
        mock_print.assert_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        config_error_found = any("設定が不正です" in call for call in print_calls)
        assert config_error_found

        # 終了コードが1であること
        assert exit_code == 1
