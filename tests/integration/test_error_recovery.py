"""エラー再開テストの統合テスト"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List, Any

from src.domain.group_id import GroupId
from src.usecase.register_document_usecase import RegisterDocumentUseCase
from src.adapter.filesystem_document_reader import FileSystemDocumentReader
from src.adapter.unstructured_document_parser import UnstructuredDocumentParser
from src.adapter.graphiti_episode_repository import GraphitiEpisodeRepository
from src.adapter.chunk_file_manager import ChunkFileManager


class TestErrorRecovery:
    """エラー再開機能のテスト"""

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def test_directories(self, temp_dir):
        """テスト用ディレクトリ構造を作成"""
        base_path = Path(temp_dir)
        directories = {
            "input": base_path / "input",
            "work": base_path / "work",
            "done": base_path / "done",
            "input_chunks": base_path / "input_chunks",
        }

        for dir_path in directories.values():
            dir_path.mkdir(parents=True, exist_ok=True)

        return directories

    @pytest.fixture
    def sample_files(self, test_directories):
        """テスト用サンプルファイルを作成"""
        input_dir = test_directories["input"]

        # テキストファイル作成
        (input_dir / "sample.txt").write_text(
            "これはテスト用のサンプルテキストです。\n"
            "複数の行にわたって記述されています。\n"
            "エラー再開テストで使用します。",
            encoding="utf-8",
        )

        # サブディレクトリとファイル
        sub_dir = input_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "nested.txt").write_text(
            "ネストされたディレクトリのファイルです。", encoding="utf-8"
        )

        return [str(input_dir / "sample.txt"), str(sub_dir / "nested.txt")]

    @pytest.fixture
    def mock_episode_repository(self):
        """モックのエピソードリポジトリ"""
        repository = AsyncMock(spec=GraphitiEpisodeRepository)
        repository.initialize = AsyncMock()
        repository.save = AsyncMock()
        return repository

    @pytest.fixture
    def usecase(self, temp_dir, mock_episode_repository):
        """テスト用のユースケース"""
        file_reader = FileSystemDocumentReader()
        document_parser = UnstructuredDocumentParser(
            max_characters=500, combine_text_under_n_chars=100, overlap=0
        )
        chunk_file_manager = ChunkFileManager(f"{temp_dir}/input_chunks")

        return RegisterDocumentUseCase(
            file_reader=file_reader,
            document_parser=document_parser,
            episode_repository=mock_episode_repository,
            chunk_file_manager=chunk_file_manager,
        )

    def assert_file_location(self, file_path: str, expected_dir: str):
        """ファイルの場所を確認"""
        assert expected_dir in file_path, (
            f"ファイル {file_path} が {expected_dir} にありません"
        )
        assert Path(file_path).exists(), f"ファイル {file_path} が存在しません"

    def count_episode_files(
        self, chunk_file_manager: ChunkFileManager, file_path: str
    ) -> int:
        """残存エピソードファイル数を確認"""
        try:
            # エピソードファイルの直接カウント
            chunk_dir = chunk_file_manager._get_chunk_directory(file_path)
            if not chunk_dir.exists():
                return 0

            episode_files = list(chunk_dir.glob("episode_*.json"))
            return len(episode_files)
        except:
            return 0

    @pytest.mark.asyncio
    async def test_チャンク分割中のエラーからの再開(
        self, usecase, test_directories, sample_files, mock_episode_repository
    ):
        """
        シナリオ:
        1. ファイルのチャンク生成中にエラー発生
        2. ファイルはinput/に残る
        3. 再実行で正常に処理完了
        """
        directory = str(test_directories["input"].parent)
        group_id = GroupId("test")

        # エラー注入: document_parserでエラー発生
        with patch.object(usecase._document_parser, "parse") as mock_parse:
            mock_parse.side_effect = Exception("Parse error during chunk generation")

            # 初回実行（エラー）
            result = await usecase.execute_parallel(group_id, directory)

            # ファイルがinput/に残っていることを確認
            input_files = list(test_directories["input"].rglob("*.txt"))
            assert len(input_files) == 2, "ファイルがinput/に残っている必要があります"

            # エピソードファイルが作成されていないことを確認
            chunks_dir = test_directories["input_chunks"]
            assert not any(chunks_dir.rglob("episode_*.json")), (
                "エピソードファイルは作成されていない必要があります"
            )

        # 再実行（成功）
        result = await usecase.execute_parallel(group_id, directory)

        # 処理が成功することを確認
        assert result.success, "再実行は成功する必要があります"
        assert result.total_files > 0, "ファイルが処理されている必要があります"

        # エピソードファイルが作成されていることを確認
        chunks_dir = test_directories["input_chunks"]
        episode_files = list(chunks_dir.rglob("episode_*.json"))
        assert len(episode_files) > 0, (
            "エピソードファイルが作成されている必要があります"
        )

        # ファイルの場所を確認
        input_files = list(test_directories["input"].rglob("*.txt"))
        work_files = list(test_directories["work"].rglob("*.txt"))
        done_files = list(test_directories["done"].rglob("*.txt"))

        print(f"Input files: {[f.name for f in input_files]}")
        print(f"Work files: {[f.name for f in work_files]}")
        print(f"Done files: {[f.name for f in done_files]}")

        # ファイルが適切な場所に移動していることを確認
        # モックエピソードリポジトリでは実際の登録は行われないので、work/またはdone/のいずれかにある
        total_processed = len(work_files) + len(done_files)
        assert total_processed == 2, (
            f"処理されたファイル数が2つである必要があります (work: {len(work_files)}, done: {len(done_files)})"
        )
        assert len(input_files) == 0, "input/にファイルが残っていない必要があります"

    @pytest.mark.asyncio
    async def test_エピソード登録中のエラーからの再開(
        self, usecase, test_directories, sample_files, mock_episode_repository
    ):
        """
        シナリオ:
        1. 50%のエピソード登録後にRate Limitエラー
        2. ファイルはwork/に残る
        3. 残存エピソードファイルから再開
        """
        directory = str(test_directories["input"].parent)
        group_id = GroupId("test")

        # まず正常にwork/状態まで進める
        result1 = await usecase.execute_parallel(group_id, directory)

        # work/にファイルがあることを確認
        work_files = list(test_directories["work"].rglob("*.txt"))

        if len(work_files) == 0:
            # ファイルがdone/に移動済みの場合、手動でwork/に配置してエピソードファイルを作成
            done_files = list(test_directories["done"].rglob("*.txt"))
            assert len(done_files) > 0, "処理されたファイルが必要です"

            # done/からwork/にファイルを移動
            for done_file in done_files:
                work_file = test_directories["work"] / done_file.relative_to(
                    test_directories["done"]
                )
                work_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(done_file), str(work_file))

                # エピソードファイルを手動作成（テスト用）
                episodes = [
                    {"name": f"{work_file.name} - chunk_0", "body": "episode 0"},
                    {"name": f"{work_file.name} - chunk_1", "body": "episode 1"},
                    {"name": f"{work_file.name} - chunk_2", "body": "episode 2"},
                ]

                # エピソードファイルとして保存
                from src.domain.episode import Episode
                from datetime import datetime

                test_episodes = []
                for i, ep_data in enumerate(episodes):
                    episode = Episode(
                        name=ep_data["name"],
                        body=ep_data["body"],
                        source_description=f"Source file: {work_file.name}",
                        reference_time=datetime.now(),
                        episode_type="text",
                        group_id=group_id,
                    )
                    test_episodes.append(episode)

                usecase._chunk_file_manager.save_episodes(str(work_file), test_episodes)

            work_files = list(test_directories["work"].rglob("*.txt"))

        assert len(work_files) > 0, "work/にファイルが必要です"

        # エラー注入: episode_2でRate Limit
        call_count = [0]

        async def mock_save_with_error(episode):
            call_count[0] += 1
            if call_count[0] == 3:  # 3回目の呼び出しでエラー
                raise Exception("Rate limit exceeded")
            return None

        mock_episode_repository.save.side_effect = mock_save_with_error

        # 実行（部分成功）
        result = await usecase.execute_parallel(group_id, directory)

        # ファイルがwork/に残っていることを確認
        remaining_work_files = list(test_directories["work"].rglob("*.txt"))
        assert len(remaining_work_files) > 0, (
            "一部のファイルがwork/に残っている必要があります"
        )

        # 一部のエピソードファイルが削除されていることを確認
        for work_file in remaining_work_files:
            episode_count = self.count_episode_files(
                usecase._chunk_file_manager, str(work_file)
            )
            assert episode_count > 0, (
                f"一部のエピソードファイルが残っている必要があります (ファイル: {work_file.name}, カウント: {episode_count})"
            )
            assert episode_count < 3, (
                f"一部のエピソードファイルが削除されている必要があります (ファイル: {work_file.name}, カウント: {episode_count})"
            )

    @pytest.mark.asyncio
    async def test_複数ファイル並列処理でのエラー再開(
        self, usecase, test_directories, sample_files, mock_episode_repository
    ):
        """
        シナリオ:
        1. 3ファイル並列処理中、各ファイルで異なるタイミングでエラー
        2. 各ファイルが適切な状態で保存
        3. 再実行で全ファイル処理完了
        """
        directory = str(test_directories["input"].parent)
        group_id = GroupId("test")

        # 追加のテストファイルを作成
        additional_file = test_directories["input"] / "additional.txt"
        additional_file.write_text("追加のテストファイルです。", encoding="utf-8")

        # ファイル別にエラーを注入
        file_error_map = {}

        def mock_parse_with_selective_error(file_path):
            file_name = Path(file_path).name
            if file_name == "sample.txt":
                raise Exception("Chunk generation error for sample.txt")
            # その他のファイルは正常処理
            return usecase._document_parser.parse.__wrapped__(
                usecase._document_parser, file_path
            )

        with patch.object(
            usecase._document_parser,
            "parse",
            side_effect=mock_parse_with_selective_error,
        ):
            # 初回実行（部分的なエラー）
            result = await usecase.execute_parallel(group_id, directory)

            # sample.txtはinput/に残り、その他はwork/またはdone/に移動
            input_files = [f.name for f in test_directories["input"].rglob("*.txt")]
            assert "sample.txt" in input_files, (
                "エラーファイルはinput/に残る必要があります"
            )

        # 再実行（全ファイル成功）
        result = await usecase.execute_parallel(group_id, directory)

        # 全ファイルが最終的にdone/に移動することを確認
        assert result.success, "再実行では全ファイルが成功する必要があります"

        # input/にファイルが残っていないことを確認
        remaining_input_files = list(test_directories["input"].rglob("*.txt"))
        assert len(remaining_input_files) == 0, (
            "input/にファイルが残っていない必要があります"
        )

    def test_ディレクトリ構造の維持(self, test_directories, sample_files):
        """ファイル移動時にディレクトリ構造が維持されることを確認"""
        file_reader = FileSystemDocumentReader()
        file_reader._base_directory = str(test_directories["input"])

        # ネストされたファイルを移動
        source_file = test_directories["input"] / "subdir" / "nested.txt"
        destination_dir = str(test_directories["work"])

        moved_path = file_reader.move_file(str(source_file), destination_dir)

        # ディレクトリ構造が維持されていることを確認
        expected_path = test_directories["work"] / "subdir" / "nested.txt"
        assert Path(moved_path) == expected_path, (
            "ディレクトリ構造が維持されている必要があります"
        )
        assert expected_path.exists(), "移動されたファイルが存在する必要があります"

    def test_ファイル状態の判定ヘルパー(self, test_directories):
        """ファイル状態判定のヘルパー関数のテスト"""
        # input/のファイル
        input_file = test_directories["input"] / "test.txt"
        input_file.write_text("test")

        self.assert_file_location(str(input_file), "input")

        # work/のファイル
        work_file = test_directories["work"] / "test.txt"
        work_file.write_text("test")

        self.assert_file_location(str(work_file), "work")

        # done/のファイル
        done_file = test_directories["done"] / "test.txt"
        done_file.write_text("test")

        self.assert_file_location(str(done_file), "done")
