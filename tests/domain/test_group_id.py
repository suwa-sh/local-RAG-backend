"""GroupId値オブジェクトのテスト"""

import pytest
from src.domain.group_id import GroupId


class TestGroupId:
    """GroupId値オブジェクトのテストクラス"""

    def test_GroupId作成_正常な値を指定した場合_インスタンスが作成されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        value = "default"

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        group_id = GroupId(value)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert group_id.value == value

    def test_GroupId作成_空文字を指定した場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        value = ""

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(ValueError, match="GroupIdは空文字列にできません"):
            GroupId(value)

    def test_GroupId作成_Noneを指定した場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        value = None

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(ValueError, match="GroupIdは空文字列にできません"):
            GroupId(value)

    def test_GroupId作成_スペースのみを指定した場合_例外が発生すること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        value = "   "

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        with pytest.raises(ValueError, match="GroupIdは空文字列にできません"):
            GroupId(value)

    def test_GroupId等価性_同じ値のインスタンス同士_等しいこと(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        value = "test-group"
        group_id1 = GroupId(value)
        group_id2 = GroupId(value)

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        assert group_id1 == group_id2

    def test_GroupId等価性_異なる値のインスタンス同士_等しくないこと(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        group_id1 = GroupId("group1")
        group_id2 = GroupId("group2")

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        assert group_id1 != group_id2

    def test_GroupIdハッシュ_同じ値のインスタンス同士_同じハッシュ値であること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        value = "test-group"
        group_id1 = GroupId(value)
        group_id2 = GroupId(value)

        # ------------------------------
        # 実行 (Act) & 検証 (Assert)
        # ------------------------------
        assert hash(group_id1) == hash(group_id2)

    def test_GroupId文字列表現_valueが返されること(self):
        # ------------------------------
        # 準備 (Arrange)
        # ------------------------------
        value = "sample-group"
        group_id = GroupId(value)

        # ------------------------------
        # 実行 (Act)
        # ------------------------------
        result = str(group_id)

        # ------------------------------
        # 検証 (Assert)
        # ------------------------------
        assert result == value
