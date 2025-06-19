"""UnstructuredDocumentParser - Unstructured.ioライブラリとの連携"""

from typing import List, Any, Dict
from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title
from src.domain.document import Document
from src.domain.chunk import Chunk


class UnstructuredDocumentParser:
    """Unstructured.ioを使用したドキュメント解析器"""

    def __init__(
        self,
        max_characters: int = 1000,
        combine_text_under_n_chars: int = 100,
        overlap: int = 0,
    ) -> None:
        """
        UnstructuredDocumentParserを初期化する

        Args:
            max_characters: チャンクの最大文字数
            combine_text_under_n_chars: この文字数未満のテキストは前のチャンクと結合
            overlap: チャンク間のオーバーラップ文字数
        """
        self.max_characters = max_characters
        self.combine_text_under_n_chars = combine_text_under_n_chars
        self.overlap = overlap

    def parse(self, file_path: str) -> List[Any]:
        """
        ファイルを解析してElementリストを取得する

        Args:
            file_path: 解析するファイルのパス

        Returns:
            List[Any]: Unstructuredライブラリから返されるElementのリスト

        Raises:
            FileNotFoundError: ファイルが存在しない場合
        """
        try:
            elements = partition(filename=file_path)
            return elements
        except FileNotFoundError as e:
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}") from e

    def split_elements(
        self, elements: List[Any], source_document: Document
    ) -> List[Chunk]:
        """
        ElementリストをChunkリストに変換する

        Args:
            elements: Unstructuredライブラリから取得したElementのリスト
            source_document: ソースドキュメント

        Returns:
            List[Chunk]: 作成されたChunkのリスト
        """
        if not elements:
            return []

        # Unstructuredのchunk_elementsを使用してチャンク化
        # より意味的な境界での分割を促進するために70%で新チャンクを開始
        chunks_elements = chunk_by_title(
            elements,
            max_characters=self.max_characters,
            combine_text_under_n_chars=self.combine_text_under_n_chars,
            new_after_n_chars=int(self.max_characters * 0.7),
            overlap=self.overlap,
        )

        # UnstructuredのチャンクをドメインのChunkオブジェクトに変換
        chunks = []
        for i, chunk_element in enumerate(chunks_elements):
            chunk_text = str(chunk_element).strip()
            if not chunk_text:
                continue

            # チャンクのメタデータを取得
            element_metadata = getattr(chunk_element, "metadata", None)
            if element_metadata and hasattr(element_metadata, "to_dict"):
                chunk_metadata = element_metadata.to_dict()
            else:
                chunk_metadata = {}

            chunk = self._create_chunk(
                index=i,
                text=chunk_text,
                metadata=chunk_metadata,
                source_document=source_document,
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self, index: int, text: str, metadata: Dict[str, Any], source_document: Document
    ) -> Chunk:
        """
        Chunkインスタンスを作成する

        Args:
            index: チャンクのインデックス
            text: チャンクのテキスト
            metadata: チャンクのメタデータ
            source_document: ソースドキュメント

        Returns:
            Chunk: 作成されたChunkインスタンス
        """
        chunk_id = f"{source_document.relative_path}_chunk_{index}"
        chunk_metadata = {
            "original_chunk_id": f"chunk_{index}",
            "position": index,
            **metadata,
        }

        return Chunk(
            id=chunk_id,
            text=text,
            metadata=chunk_metadata,
            source_document=source_document,
        )
