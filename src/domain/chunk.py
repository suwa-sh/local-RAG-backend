"""Chunk値オブジェクト"""

from datetime import datetime
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .document import Document
    from .episode import Episode
    from .group_id import GroupId


class Chunk:
    """チャンクを表す値オブジェクト"""

    def __init__(
        self,
        id: str,
        text: str,
        metadata: Dict[str, Any],
        source_document: "Document",
    ) -> None:
        """
        Chunkを作成する

        Args:
            id: チャンクID
            text: チャンクのテキスト内容
            metadata: チャンクのメタデータ
            source_document: ソースドキュメント

        Raises:
            ValueError: idまたはtextが空文字列の場合
        """
        if not id or not id.strip():
            raise ValueError("idは空文字列にできません")
        if not text or not text.strip():
            raise ValueError("textは空文字列にできません")

        self._id = id
        self._text = text
        self._metadata = metadata.copy() if metadata else {}
        self._source_document = source_document

    @property
    def id(self) -> str:
        """チャンクIDを取得する"""
        return self._id

    @property
    def text(self) -> str:
        """チャンクテキストを取得する"""
        return self._text

    @property
    def metadata(self) -> Dict[str, Any]:
        """チャンクメタデータを取得する"""
        return self._metadata.copy()

    @property
    def source_document(self) -> "Document":
        """ソースドキュメントを取得する"""
        return self._source_document

    def to_episode(self, group_id: "GroupId") -> "Episode":
        """
        チャンクからエピソードを作成する

        Args:
            group_id: グループID

        Returns:
            Episode: 作成されたエピソード
        """
        from .episode import Episode

        name = f"{self._source_document.relative_path} - chunk_{self._metadata.get('position', 0)}"
        body = self._text
        source_description = f"Source file: {self._source_document.relative_path}"
        reference_time = self._source_document.file_last_modified
        episode_type = "text"

        return Episode(
            name=name,
            body=body,
            source_description=source_description,
            reference_time=reference_time,
            episode_type=episode_type,
            group_id=group_id,
        )

    def __eq__(self, other: object) -> bool:
        """等価性判定"""
        if not isinstance(other, Chunk):
            return False
        return (
            self._id == other._id
            and self._text == other._text
            and self._metadata == other._metadata
            and self._source_document == other._source_document
        )

    def __hash__(self) -> int:
        """ハッシュ値計算"""
        # metadataはdictなのでhashableにするため、sorted itemsのtupleに変換
        metadata_tuple = tuple(sorted(self._metadata.items()))
        return hash((self._id, self._text, metadata_tuple, self._source_document))

    def __str__(self) -> str:
        """文字列表現"""
        return f"{self._id}: {self._text[:50]}..."

    def __repr__(self) -> str:
        """開発者向け文字列表現"""
        return (
            f"Chunk(id='{self._id}', text='{self._text[:30]}...', "
            f"metadata={self._metadata}, source_document={self._source_document.file_name})"
        )
