"""Document値オブジェクト"""

from datetime import datetime
from pathlib import Path
from typing import Set, ClassVar


class Document:
    """文書を表す値オブジェクト"""

    # サポートされているファイルタイプ（Unstructured.io公式サポート準拠）
    SUPPORTED_FILE_TYPES: ClassVar[Set[str]] = {
        "bmp",
        "csv",
        "doc",
        "docx",
        "eml",
        "epub",
        "heic",
        "html",
        "jpeg",
        "jpg",  # jpegの一般的な拡張子
        "png",
        "md",
        "msg",
        "odt",
        "org",
        "p7s",
        "pdf",
        "ppt",
        "pptx",
        "rst",
        "rtf",
        "tiff",
        "tif",  # tiffの一般的な拡張子
        "txt",
        "tsv",
        "xls",
        "xlsx",
        "xml",
    }

    def __init__(
        self,
        file_path: str,
        file_name: str,
        file_type: str,
        content: str,
        file_last_modified: datetime,
        relative_path: str | None = None,
    ) -> None:
        """
        Documentを作成する

        Args:
            file_path: ファイルパス
            file_name: ファイル名
            file_type: ファイルタイプ（拡張子）
            content: ファイル内容
            file_last_modified: ファイルの最終更新日時
            relative_path: 基準ディレクトリからの相対パス（Noneの場合はfile_nameを使用）

        Raises:
            ValueError: file_path、file_name、contentが空文字列の場合、
                       またはサポートされていないfile_typeの場合
        """
        if not file_path or not file_path.strip():
            raise ValueError("file_pathは空文字列にできません")
        if not file_name or not file_name.strip():
            raise ValueError("file_nameは空文字列にできません")
        if not content or not content.strip():
            raise ValueError("contentは空文字列にできません")
        if file_type not in self.SUPPORTED_FILE_TYPES:
            raise ValueError("サポートされていないfile_typeです")

        self._file_path = file_path
        self._file_name = file_name
        self._file_type = file_type
        self._content = content
        self._file_last_modified = file_last_modified
        self._relative_path = relative_path or file_name

    @property
    def file_path(self) -> str:
        """ファイルパスを取得する"""
        return self._file_path

    @file_path.setter
    def file_path(self, value: str) -> None:
        """ファイルパスを設定する"""
        self._file_path = value

    @property
    def file_name(self) -> str:
        """ファイル名を取得する"""
        return self._file_name

    @property
    def file_type(self) -> str:
        """ファイルタイプを取得する"""
        return self._file_type

    @property
    def content(self) -> str:
        """ファイル内容を取得する"""
        return self._content

    @property
    def file_last_modified(self) -> datetime:
        """ファイルの最終更新日時を取得する"""
        return self._file_last_modified

    @property
    def relative_path(self) -> str:
        """基準ディレクトリからの相対パスを取得する"""
        return self._relative_path

    @classmethod
    def from_file(cls, file_path: str, base_directory: str | None = None) -> "Document":
        """
        ファイルパスからDocumentを作成する

        Args:
            file_path: 読み込むファイルのパス
            base_directory: 相対パス計算の基準ディレクトリ（Noneの場合はファイル名のみ使用）

        Returns:
            Document: 作成されたDocumentインスタンス

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: サポートされていないファイルタイプの場合
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        file_name = path.name
        file_type = path.suffix.lstrip(".").lower()

        # ファイル内容を読み込み
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # バイナリファイルの場合は内容を文字列として表現
            content = f"<バイナリファイル: {file_name}>"

        # ファイルの最終更新日時を取得
        file_last_modified = datetime.fromtimestamp(path.stat().st_mtime)

        # 相対パスを計算
        if base_directory:
            base_path = Path(base_directory).resolve()
            absolute_path = path.resolve()
            try:
                relative_path = str(absolute_path.relative_to(base_path))
            except ValueError:
                # base_directoryの外部にある場合はファイル名のみ使用
                relative_path = file_name
        else:
            relative_path = file_name

        return cls(
            file_path=str(path.absolute()),
            file_name=file_name,
            file_type=file_type,
            content=content,
            file_last_modified=file_last_modified,
            relative_path=relative_path,
        )

    def __eq__(self, other: object) -> bool:
        """等価性判定"""
        if not isinstance(other, Document):
            return False
        return (
            self._file_path == other._file_path
            and self._file_name == other._file_name
            and self._file_type == other._file_type
            and self._content == other._content
            and self._file_last_modified == other._file_last_modified
            and self._relative_path == other._relative_path
        )

    def __hash__(self) -> int:
        """ハッシュ値計算"""
        return hash(
            (
                self._file_path,
                self._file_name,
                self._file_type,
                self._content,
                self._file_last_modified,
                self._relative_path,
            )
        )

    def __str__(self) -> str:
        """文字列表現"""
        return f"{self._file_name} ({self._file_type})"

    def __repr__(self) -> str:
        """開発者向け文字列表現"""
        return (
            f"Document(file_path='{self._file_path}', file_name='{self._file_name}', "
            f"file_type='{self._file_type}', content='{self._content[:50]}...')"
        )
