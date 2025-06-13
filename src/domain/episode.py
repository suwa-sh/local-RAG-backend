"""Episode値オブジェクト"""

from datetime import datetime
from typing import Set
from .group_id import GroupId


class Episode:
    """エピソードを表す値オブジェクト"""

    # サポートされているエピソードタイプ
    SUPPORTED_EPISODE_TYPES: Set[str] = {"text", "image", "audio", "video"}

    def __init__(
        self,
        name: str,
        body: str,
        source_description: str,
        reference_time: datetime,
        episode_type: str,
        group_id: GroupId,
    ) -> None:
        """
        Episodeを作成する

        Args:
            name: エピソード名
            body: エピソードの本文
            source_description: ソースファイルの説明
            reference_time: 参照時刻
            episode_type: エピソードタイプ（text, image, audio, video）
            group_id: グループID

        Raises:
            ValueError: nameまたはbodyが空文字列の場合、またはサポートされていないepisode_typeの場合
        """
        if not name or not name.strip():
            raise ValueError("nameは空文字列にできません")
        if not body or not body.strip():
            raise ValueError("bodyは空文字列にできません")
        if episode_type not in self.SUPPORTED_EPISODE_TYPES:
            raise ValueError("サポートされていないepisode_typeです")

        self._name = name
        self._body = body
        self._source_description = source_description
        self._reference_time = reference_time
        self._episode_type = episode_type
        self._group_id = group_id

    @property
    def name(self) -> str:
        """エピソード名を取得する"""
        return self._name

    @property
    def body(self) -> str:
        """エピソード本文を取得する"""
        return self._body

    @property
    def source_description(self) -> str:
        """ソース説明を取得する"""
        return self._source_description

    @property
    def reference_time(self) -> datetime:
        """参照時刻を取得する"""
        return self._reference_time

    @property
    def episode_type(self) -> str:
        """エピソードタイプを取得する"""
        return self._episode_type

    @property
    def group_id(self) -> GroupId:
        """グループIDを取得する"""
        return self._group_id

    def __eq__(self, other: object) -> bool:
        """等価性判定"""
        if not isinstance(other, Episode):
            return False
        return (
            self._name == other._name
            and self._body == other._body
            and self._source_description == other._source_description
            and self._reference_time == other._reference_time
            and self._episode_type == other._episode_type
            and self._group_id == other._group_id
        )

    def __hash__(self) -> int:
        """ハッシュ値計算"""
        return hash(
            (
                self._name,
                self._body,
                self._source_description,
                self._reference_time,
                self._episode_type,
                self._group_id,
            )
        )

    def __str__(self) -> str:
        """文字列表現"""
        return f"{self._name} ({self._episode_type})"

    def __repr__(self) -> str:
        """開発者向け文字列表現"""
        return (
            f"Episode(name='{self._name}', body='{self._body[:50]}...', "
            f"episode_type='{self._episode_type}', group_id={self._group_id!r})"
        )
