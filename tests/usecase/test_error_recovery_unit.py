"""エラー再開機能のユニットテスト"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.adapter.chunk_file_manager import ChunkFileManager
from src.adapter.filesystem_document_reader import FileSystemDocumentReader
from src.domain.episode import Episode
from src.domain.group_id import GroupId
from datetime import datetime


class TestErrorRecoveryUnit:
    """エラー再開機能のユニットテスト"""

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
    def chunk_file_manager(self, test_directories):
        """テスト用のチャンクファイルマネージャー"""
        return ChunkFileManager(str(test_directories["input_chunks"]))

    @pytest.fixture
    def file_reader(self, test_directories):
        """テスト用のファイルリーダー"""
        reader = FileSystemDocumentReader()
        reader._base_directory = str(test_directories["input"])
        return reader

    @pytest.fixture
    def sample_episodes(self):
        """テスト用のサンプルエピソード"""
        group_id = GroupId("test")
        episodes = []

        for i in range(5):
            episode = Episode(
                name=f"test.txt - chunk_{i}",
                body=f"これはチャンク{i}のテキストです。",
                source_description="Source file: test.txt",
                reference_time=datetime.now(),
                episode_type="text",
                group_id=group_id,
            )
            episodes.append(episode)

        return episodes

    def test_エピソードファイルの事前保存(
        self, chunk_file_manager, sample_episodes, test_directories
    ):
        """エピソードファイルが正しく事前保存されることを確認"""
        file_path = str(test_directories["input"] / "test.txt")

        # エピソードを事前保存
        chunk_file_manager.save_episodes(file_path, sample_episodes)

        # 保存されたエピソードファイルを確認
        for i in range(len(sample_episodes)):
            episode_file = chunk_file_manager._get_episode_file_path(file_path, i)
            assert episode_file.exists(), (
                f"エピソードファイル {i} が存在する必要があります"
            )

        # エピソードファイルの存在確認
        assert chunk_file_manager.has_saved_episodes(file_path), (
            "エピソードファイルが存在する必要があります"
        )

    def test_エピソードファイルの部分削除(
        self, chunk_file_manager, sample_episodes, test_directories
    ):
        """エピソードファイルが部分的に削除されることを確認"""
        file_path = str(test_directories["input"] / "test.txt")

        # エピソードを事前保存
        chunk_file_manager.save_episodes(file_path, sample_episodes)

        # 最初の2つのエピソードファイルを削除（保存成功をシミュレート）
        chunk_file_manager.delete_episode_files(file_path, 0, 1)

        # 削除されたファイルが存在しないことを確認
        for i in range(2):
            episode_file = chunk_file_manager._get_episode_file_path(file_path, i)
            assert not episode_file.exists(), (
                f"エピソードファイル {i} は削除されている必要があります"
            )

        # 残りのファイルが存在することを確認
        for i in range(2, len(sample_episodes)):
            episode_file = chunk_file_manager._get_episode_file_path(file_path, i)
            assert episode_file.exists(), (
                f"エピソードファイル {i} は残っている必要があります"
            )

        # まだエピソードファイルが存在することを確認
        assert chunk_file_manager.has_saved_episodes(file_path), (
            "残りのエピソードファイルが存在する必要があります"
        )

    def test_全エピソードファイル削除後の状態(
        self, chunk_file_manager, sample_episodes, test_directories
    ):
        """全エピソードファイル削除後の状態確認"""
        file_path = str(test_directories["input"] / "test.txt")

        # エピソードを事前保存
        chunk_file_manager.save_episodes(file_path, sample_episodes)

        # 全エピソードファイルを削除
        chunk_file_manager.delete_episode_files(file_path, 0, len(sample_episodes) - 1)

        # エピソードファイルが存在しないことを確認
        assert not chunk_file_manager.has_saved_episodes(file_path), (
            "エピソードファイルは存在しない必要があります"
        )

    def test_エピソードファイルの読み込み(
        self, chunk_file_manager, sample_episodes, test_directories
    ):
        """保存されたエピソードファイルが正しく読み込まれることを確認"""
        file_path = str(test_directories["input"] / "test.txt")

        # エピソードを事前保存
        chunk_file_manager.save_episodes(file_path, sample_episodes)

        # エピソードを読み込み
        loaded_episodes = chunk_file_manager.load_episodes(file_path)

        # 読み込まれたエピソードの確認
        assert len(loaded_episodes) == len(sample_episodes), (
            "エピソード数が一致する必要があります"
        )

        for i, (original, loaded) in enumerate(zip(sample_episodes, loaded_episodes)):
            assert original.name == loaded.name, (
                f"エピソード {i} の名前が一致する必要があります"
            )
            assert original.body == loaded.body, (
                f"エピソード {i} の本文が一致する必要があります"
            )
            assert original.episode_type == loaded.episode_type, (
                f"エピソード {i} のタイプが一致する必要があります"
            )

    def test_ファイル移動でのディレクトリ構造維持(self, file_reader, test_directories):
        """ファイル移動時にディレクトリ構造が維持されることを確認"""
        # ネストされたファイルを作成
        source_file = test_directories["input"] / "subdir" / "nested.txt"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text("ネストされたファイル", encoding="utf-8")

        # work/ディレクトリに移動
        moved_path = file_reader.move_file(
            str(source_file), str(test_directories["work"])
        )

        # ディレクトリ構造が維持されていることを確認
        expected_path = test_directories["work"] / "subdir" / "nested.txt"
        assert Path(moved_path) == expected_path, "移動後のパスが正しくない"
        assert expected_path.exists(), "移動されたファイルが存在しない"
        assert not source_file.exists(), "元ファイルが削除されていない"

    def test_同名ファイルがある場合の移動(self, file_reader, test_directories):
        """移動先に同名ファイルがある場合の処理確認"""
        # 元ファイル作成
        source_file = test_directories["input"] / "duplicate.txt"
        source_file.write_text("元ファイル", encoding="utf-8")

        # 移動先に同名ファイル作成
        existing_file = test_directories["work"] / "duplicate.txt"
        existing_file.write_text("既存ファイル", encoding="utf-8")

        # ファイル移動（タイムスタンプ付きの名前になるはず）
        moved_path = file_reader.move_file(
            str(source_file), str(test_directories["work"])
        )

        # 元ファイルと既存ファイルの両方が存在することを確認
        assert Path(moved_path).exists(), "移動されたファイルが存在しない"
        assert existing_file.exists(), "既存ファイルが残っている必要がある"
        assert Path(moved_path) != existing_file, (
            "移動されたファイルは既存ファイルと異なる名前である必要がある"
        )
        assert "_" in Path(moved_path).stem, (
            "移動されたファイルにはタイムスタンプが含まれている必要がある"
        )

    def test_ファイル存在チェック(self, chunk_file_manager, test_directories):
        """ファイル存在チェックの動作確認"""
        file_path = str(test_directories["input"] / "nonexistent.txt")

        # 存在しないファイルのチェック
        assert not chunk_file_manager.has_saved_episodes(file_path), (
            "存在しないファイルのエピソードファイルは存在しない"
        )

        # ディレクトリが存在しない場合
        nonexistent_path = str(
            test_directories["input"] / "nonexistent_dir" / "file.txt"
        )
        assert not chunk_file_manager.has_saved_episodes(nonexistent_path), (
            "存在しないディレクトリのファイルは存在しない"
        )

    def test_エピソードファイルのメタデータ整合性(
        self, chunk_file_manager, sample_episodes, test_directories
    ):
        """エピソードファイルのメタデータが正しく保存・復元されることを確認"""
        file_path = str(test_directories["input"] / "metadata_test.txt")

        # 特定のメタデータを持つエピソードを作成
        special_episode = Episode(
            name="special_test.txt - chunk_0",
            body="特別なテストエピソード",
            source_description="Source file: special_test.txt",
            reference_time=datetime(2025, 6, 20, 10, 30, 45),
            episode_type="text",
            group_id=GroupId("special_group"),
        )

        # エピソードを保存
        chunk_file_manager.save_episodes(file_path, [special_episode])

        # エピソードを読み込み
        loaded_episodes = chunk_file_manager.load_episodes(file_path)

        # メタデータの整合性確認
        loaded_episode = loaded_episodes[0]
        assert loaded_episode.name == special_episode.name
        assert loaded_episode.body == special_episode.body
        assert loaded_episode.source_description == special_episode.source_description
        assert loaded_episode.reference_time == special_episode.reference_time
        assert loaded_episode.episode_type == special_episode.episode_type
        assert loaded_episode.group_id.value == special_episode.group_id.value
