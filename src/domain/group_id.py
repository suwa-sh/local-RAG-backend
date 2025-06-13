"""GroupId値オブジェクト"""

from typing import Optional


class GroupId:
    """グループIDを表す値オブジェクト"""

    def __init__(self, value: Optional[str]) -> None:
        """
        GroupIdを作成する

        Args:
            value: グループID文字列

        Raises:
            ValueError: valueが空文字列またはNoneの場合
        """
        if not value or not value.strip():
            raise ValueError("GroupIdは空文字列にできません")
        self._value = value

    @property
    def value(self) -> str:
        """グループID値を取得する"""
        return self._value

    def __eq__(self, other: object) -> bool:
        """等価性判定"""
        if not isinstance(other, GroupId):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        """ハッシュ値計算"""
        return hash(self._value)

    def __str__(self) -> str:
        """文字列表現"""
        return self._value

    def __repr__(self) -> str:
        """開発者向け文字列表現"""
        return f"GroupId('{self._value}')"
