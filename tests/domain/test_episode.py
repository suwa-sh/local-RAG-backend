"""Episode値オブジェクトのテスト"""

import pytest
from datetime import datetime
from src.domain.episode import Episode
from src.domain.group_id import GroupId


class TestEpisode:
    """Episode値オブジェクトのテストクラス"""

    def test_Episode作成_正常な値を指定した場合_インスタンスが作成されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        name = "sample.pdf - chunk 0"
        body = "This is the first chunk..."
        source_description = "Source file: sample.pdf"
        reference_time = datetime(2025, 6, 13, 10, 0, 0)
        episode_type = "text"
        group_id = GroupId("default")

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        episode = Episode(
            name=name,
            body=body,
            source_description=source_description,
            reference_time=reference_time,
            episode_type=episode_type,
            group_id=group_id,
        )

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert episode.name == name
        assert episode.body == body
        assert episode.source_description == source_description
        assert episode.reference_time == reference_time
        assert episode.episode_type == episode_type
        assert episode.group_id == group_id

    def test_Episode作成_nameが空文字の場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        name = ""
        body = "Some content"
        source_description = "Source file: test.txt"
        reference_time = datetime.now()
        episode_type = "text"
        group_id = GroupId("default")

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(ValueError, match="nameは空文字列にできません"):
            Episode(
                name=name,
                body=body,
                source_description=source_description,
                reference_time=reference_time,
                episode_type=episode_type,
                group_id=group_id,
            )

    def test_Episode作成_bodyが空文字の場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        name = "test episode"
        body = ""
        source_description = "Source file: test.txt"
        reference_time = datetime.now()
        episode_type = "text"
        group_id = GroupId("default")

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(ValueError, match="bodyは空文字列にできません"):
            Episode(
                name=name,
                body=body,
                source_description=source_description,
                reference_time=reference_time,
                episode_type=episode_type,
                group_id=group_id,
            )

    def test_Episode作成_episode_typeがサポートされていない場合_例外が発生すること(
        self,
    ):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        name = "test episode"
        body = "Some content"
        source_description = "Source file: test.txt"
        reference_time = datetime.now()
        episode_type = "invalid_type"
        group_id = GroupId("default")

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(ValueError, match="サポートされていないepisode_typeです"):
            Episode(
                name=name,
                body=body,
                source_description=source_description,
                reference_time=reference_time,
                episode_type=episode_type,
                group_id=group_id,
            )

    def test_Episode等価性_同じ値のインスタンス同士_等しいこと(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        name = "test episode"
        body = "Some content"
        source_description = "Source file: test.txt"
        reference_time = datetime(2025, 6, 13, 10, 0, 0)
        episode_type = "text"
        group_id = GroupId("default")

        episode1 = Episode(
            name=name,
            body=body,
            source_description=source_description,
            reference_time=reference_time,
            episode_type=episode_type,
            group_id=group_id,
        )

        episode2 = Episode(
            name=name,
            body=body,
            source_description=source_description,
            reference_time=reference_time,
            episode_type=episode_type,
            group_id=group_id,
        )

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        assert episode1 == episode2

    def test_Episode等価性_異なる値のインスタンス同士_等しくないこと(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        reference_time = datetime(2025, 6, 13, 10, 0, 0)
        group_id = GroupId("default")

        episode1 = Episode(
            name="episode1",
            body="content1",
            source_description="file1.txt",
            reference_time=reference_time,
            episode_type="text",
            group_id=group_id,
        )

        episode2 = Episode(
            name="episode2",
            body="content2",
            source_description="file2.txt",
            reference_time=reference_time,
            episode_type="text",
            group_id=group_id,
        )

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        assert episode1 != episode2
