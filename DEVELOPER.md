# DEVELOPER.md

- v0.1.0 登録機能の設計時点

## C4モデル

### Level 1: System Context

```mermaid
graph TB
    User[ユーザー]
    System[local-RAG-backend]
    Neo4j[Neo4j Database]

    User -->|CLIコマンド実行| System
    System -->|データ登録| Neo4j
```

| 要素名            | 説明                                              |
| ----------------- | ------------------------------------------------- |
| ユーザー          | CLIコマンドを実行してドキュメントを登録する利用者 |
| local-RAG-backend | ローカルRAGシステムのバックエンド                 |
| Neo4j Database    | グラフデータベース（ベクトルDB）                  |

### Level 2: Container

```mermaid
graph TB
    CLI[CLI Application]
    DPL[Document Processing Library]
    GC[Graphiti Core]
    UN[Unstructured.io]
    Neo4j[Neo4j Database]

    CLI -->|依存| DPL
    DPL -->|使用| GC
    DPL -->|使用| UN
    GC -->|データ登録| Neo4j
```

| 要素名                      | 説明                                    |
| --------------------------- | --------------------------------------- |
| CLI Application             | ingest.pyコマンドラインインターフェース |
| Document Processing Library | ドキュメント処理のコアライブラリ        |
| Graphiti Core               | グラフDBとの連携ライブラリ              |
| Unstructured.io             | ドキュメント解析ライブラリ              |
| Neo4j Database              | グラフデータベース                      |

### Level 3: Component

```mermaid
graph TB
    subgraph "CLI Application"
        subgraph "Presentation Layer"
            ingest[ingest.py]
        end

        subgraph "Use Case Layer"
            UC[RegisterDocumentUseCase]
        end

        subgraph "Domain Layer"
            Doc[Document]
            Chunk[Chunk]
            Episode[Episode]
            GroupId[GroupId]
        end

        subgraph "Repository Layer"
            ER[EpisodeRepository]
        end

        subgraph "Adapter Layer"
            GER[GraphitiEpisodeRepository]
            UDP[UnstructuredDocumentParser]
            FDR[FileSystemDocumentReader]
        end
    end

    ingest --> UC
    UC --> Doc
    UC --> Chunk
    UC --> Episode
    UC --> GroupId
    UC --> ER
    ER -.->|実装| GER
    UC --> UDP
    UC --> FDR
```

| 要素名                     | 説明                               |
| -------------------------- | ---------------------------------- |
| ingest.py                  | CLIエントリーポイント              |
| RegisterDocumentUseCase    | ドキュメント登録のユースケース     |
| Document                   | 文書エンティティ                   |
| Chunk                      | チャンクエンティティ               |
| Episode                    | エピソード値オブジェクト           |
| GroupId                    | グループID値オブジェクト           |
| EpisodeRepository          | エピソード保存のインターフェース   |
| GraphitiEpisodeRepository  | Graphitiを使用したリポジトリ実装   |
| UnstructuredDocumentParser | Unstructuredを使用した文書解析     |
| FileSystemDocumentReader   | ファイルシステムからの文書読み込み |

## ユーザーストーリーマッピング (USM)

### エピック: ドキュメント登録

```mermaid
graph TD
    A[ドキュメントを登録する]

    B1[CLIコマンドを実行する]
    B1_1[ファイルを収集する]
    B1_2[ドキュメントを解析する]
    B1_3[チャンクに分割する]
    B1_4[グラフDBに登録する]

    C2[指定ディレクトリ内のファイルを再帰的に探索する]
    C3[サポート対象のファイル形式をフィルタリングする]
    C4[ファイルタイプを自動検出する]
    C5[ファイル内容を構造化された要素に変換する]
    C6[最大文字数制限に基づいて分割する]
    C7[短い要素は結合して適切なサイズにする]
    C8[エピソードとして登録する]
    C9[登録結果を表示する]

    A -- グループIDとディレクトリを指定 --> B1
    B1 --> B1_1
    B1 --> B1_2
    B1 --> B1_3
    B1 --> B1_4

    B1_1 --> C2
    B1_1 --> C3
    B1_2 --> C4
    B1_2 --> C5
    B1_3 --> C6
    B1_3 --> C7
    B1_4 --> C8
    B1_4 --> C9
```

| レベル | 要素                   | 説明                     |
| ------ | ---------------------- | ------------------------ |
| 活動   | ドキュメントを登録する | ユーザーの最終目的       |
| タスク | CLIコマンドを実行する  | コマンドラインからの実行 |
| 処理   | ファイルを収集する     | 対象ファイルの探索と選別 |
| 処理   | ドキュメントを解析する | ファイル内容の構造化     |
| 処理   | チャンクに分割する     | 適切なサイズへの分割     |
| 処理   | グラフDBに登録する     | Neo4jへのデータ保存      |

## アプリケーションアーキテクチャ

本プロジェクトはDDD（ドメイン駆動設計）に基づいた層構造を採用しています。

### レイヤー構造

1. **プレゼンテーション層** (`src/main/`)

   - CLIエントリーポイント
   - ユーザーインターフェース

2. **ユースケース層** (`src/usecase/`)

   - アプリケーションのビジネスロジック
   - ドメインモデルの調整

3. **ドメイン層** (`src/domain/`)

   - ビジネスルールとエンティティ
   - 値オブジェクト

4. **リポジトリ層** (`src/repository/`)

   - データ永続化のインターフェース

5. **アダプター層** (`src/adapter/`)
   - 外部サービスとの連携実装
   - リポジトリの具体的実装

## ドメインモデル

### サポートファイルタイプ

Documentクラスは、Unstructured.io公式サポートに基づいて以下のファイルタイプをサポートしています：

**参考**: [Unstructured.io - Supported File Types](https://docs.unstructured.io/open-source/introduction/supported-file-types)

| カテゴリ             | ファイルタイプ                       | 説明                           |
| -------------------- | ------------------------------------ | ------------------------------ |
| **テキスト**         | txt, md, rst, org                    | プレーンテキスト、マークダウン |
| **Web**              | html, xml                            | ウェブページ、構造化文書       |
| **PDF**              | pdf                                  | Adobe PDF文書                  |
| **Microsoft Office** | doc, docx, ppt, pptx, xls, xlsx      | Word、PowerPoint、Excel        |
| **OpenDocument**     | odt                                  | OpenOffice/LibreOffice文書     |
| **リッチテキスト**   | rtf                                  | Rich Text Format               |
| **eBook**            | epub                                 | 電子書籍                       |
| **データ**           | csv, tsv                             | カンマ区切り、タブ区切りデータ |
| **メール**           | eml, msg, p7s                        | メールメッセージ、暗号化メール |
| **画像**             | bmp, heic, jpeg, jpg, png, tiff, tif | 各種画像形式（OCR処理対象）    |

**総計**: 28種類のファイルタイプをサポート

### ドメインモデル図（オブジェクト図）

```mermaid
graph LR
    subgraph "document1: Document"
        D1[file_path: '/docs/sample.pdf']
        D2[file_name: 'sample.pdf']
        D3[file_type: 'pdf']
        D4[content: 'This is sample content...']
    end

    subgraph "chunk1: Chunk"
        C1[id: 'sample_pdf_chunk_0']
        C2[text: 'This is the first chunk...']
        C3[metadata: <br/>original_chunk_id: 'chunk_0'<br/>position: 0]
        C4[source_document: document1]
    end

    subgraph "episode1: Episode"
        E1[name: 'sample.pdf - chunk 0']
        E2[body: 'This is the first chunk...']
        E3[source_description: 'Source file: sample.pdf']
        E4[reference_time: '2025-06-13T10:00:00']
        E5[episode_type: 'text']
        E6[group_id: groupId1]
    end

    subgraph "groupId1: GroupId"
        G1[value: 'default']
    end

    C4 --> document1
    E6 --> groupId1
```

### クラス図

```mermaid
classDiagram
    class Document {
        +FilePath file_path
        +String file_name
        +String file_type
        +String content
        +from_file(path: str) Document
    }

    class Chunk {
        +String id
        +String text
        +Dict metadata
        +Document source_document
        +to_episode(group_id: GroupId) Episode
    }

    class Episode {
        +String name
        +String body
        +String source_description
        +DateTime reference_time
        +String episode_type
        +GroupId group_id
    }

    class GroupId {
        +String value
        +__init__(value: str)
        +validate()
    }

    class DocumentParser {
        <<interface>>
        +parse(file_path: str) List~Element~
    }

    class ChunkSplitter {
        <<interface>>
        +split(elements: List~Element~) List~Chunk~
    }

    class EpisodeRepository {
        <<interface>>
        +save(episode: Episode) None
        +save_batch(episodes: List~Episode~) None
    }

    Document --> Chunk : generates
    Chunk --> Episode : converts to
    Episode --> GroupId : has
    DocumentParser ..> Document : parses
    ChunkSplitter ..> Chunk : creates
    EpisodeRepository ..> Episode : persists
```

## シーケンス図

```mermaid
sequenceDiagram
    participant User
    participant CLI as ingest.py
    participant UC as RegisterDocumentUseCase
    participant FS as FileSystemDocumentReader
    participant DP as UnstructuredDocumentParser
    participant CS as ChunkSplitter
    participant ER as GraphitiEpisodeRepository
    participant Neo4j

    User->>CLI: ingest.py default /path/to/dir
    CLI->>UC: execute(group_id, directory)

    UC->>FS: list_files(directory)
    FS-->>UC: file_paths[]

    loop for each file_path
        UC->>DP: parse(file_path)
        DP-->>UC: elements[]

        UC->>CS: split(elements)
        CS-->>UC: chunks[]

        loop for each chunk
            UC->>UC: chunk.to_episode(group_id)
            UC->>ER: save(episode)
            ER->>Neo4j: add_episode()
            Neo4j-->>ER: success
            ER-->>UC: success
        end
    end

    UC-->>CLI: RegisterResult
    CLI-->>User: 登録完了メッセージ
```

## 設計上の考慮事項

### ファイルタイプサポート設計

#### 設計方針

1. **外部ライブラリ準拠**: Unstructured.ioの公式サポートに基づく
2. **一元管理**: `Document.SUPPORTED_FILE_TYPES`で集中管理
3. **拡張性**: セット型で新しいファイルタイプの追加が容易
4. **バリデーション**: 初期化時にサポート外ファイルタイプを検証

#### 技術的根拠

- **参考資料**: [Unstructured.io - Supported File Types](https://docs.unstructured.io/open-source/introduction/supported-file-types)
- **実装場所**: `src/domain/document.py:SUPPORTED_FILE_TYPES`
- **テスト保証**: 代表的なファイルタイプの動作確認済み
- **総サポート数**: 28種類のファイルタイプ

#### 将来的な拡張

```python
# 新しいファイルタイプの追加例
SUPPORTED_FILE_TYPES.add("new_format")
```

### エラーハンドリング

```mermaid
graph TD
    A[エラー種別]
    B1[ファイル読み込みエラー]
    B2[サポートされていないファイル形式]
    B3[Neo4j接続エラー]
    B4[チャンク処理エラー]

    C1[ファイルが存在しない<br/>権限不足]
    C2[未対応の拡張子<br/>破損ファイル]
    C3[ネットワーク切断<br/>認証失敗]
    C4[メモリ不足<br/>不正なデータ]

    A --> B1
    A --> B2
    A --> B3
    A --> B4

    B1 --> C1
    B2 --> C2
    B3 --> C3
    B4 --> C4
```

### パフォーマンス考慮事項

| 項目                   | 対策                       | 説明                           |
| ---------------------- | -------------------------- | ------------------------------ |
| 大量ファイルの並行処理 | 非同期処理・スレッドプール | 複数ファイルの同時処理で高速化 |
| バッチ登録による効率化 | save_batch メソッド        | 複数エピソードを一括登録       |
| メモリ使用量の最適化   | ストリーミング処理         | 大きなファイルも段階的に処理   |

### 拡張性の設計

```mermaid
graph LR
    subgraph "現在の実装"
        A1[UnstructuredDocumentParser]
        A2[GraphitiEpisodeRepository]
        A3[基本チャンク戦略]
    end

    subgraph "将来の拡張"
        B1[PDFParser<br/>DocxParser<br/>CustomParser]
        B2[ElasticsearchRepository<br/>PineconeRepository]
        B3[セマンティックチャンク<br/>オーバーラップチャンク]
    end

    A1 -.->|インターフェース実装| B1
    A2 -.->|インターフェース実装| B2
    A3 -.->|戦略パターン| B3
```

## ディレクトリ構成

### プロジェクト全体構成

```
local-RAG-backend/
├── src/                    # アプリケーションコード
│   ├── main/              # プレゼンテーション層
│   │   ├── ingest.py      # CLIエントリーポイント
│   │   └── settings.py    # 設定管理
│   ├── usecase/           # ユースケース層
│   │   └── register_document_usecase.py
│   ├── domain/            # ドメイン層
│   │   ├── document.py    # Document値オブジェクト
│   │   ├── chunk.py       # Chunk値オブジェクト
│   │   ├── episode.py     # Episode値オブジェクト
│   │   └── group_id.py    # GroupId値オブジェクト
│   └── adapter/           # アダプター層
│       ├── graphiti_episode_repository.py
│       ├── unstructured_document_parser.py
│       ├── filesystem_document_reader.py
│       ├── entity_cache.py
│       └── logging_utils.py
├── tests/                 # テストコード
│   ├── domain/           # ドメイン層テスト
│   ├── usecase/          # ユースケース層テスト
│   ├── adapter/          # アダプター層テスト
│   ├── main/             # プレゼンテーション層テスト
│   └── integration/      # 統合テスト
├── fixtures/             # テストデータ
│   └── ingest/
│       ├── test_simple/  # シンプルテスト用
│       └── test_documents/ # サンプルファイル
├── scripts/              # 開発・運用支援スクリプト
│   ├── neo4j*            # neo4j関連
│   └── analyze*          # パフォーマンス分析関連
├── .env                  # 環境変数
├── .env.example          # 環境変数テンプレート
├── CLAUDE.md            # Claude Code用ガイダンス
├── DEVELOPER.md         # 開発者向け詳細ドキュメント
├── README.md            # ユーザー向けドキュメント
├── Makefile             # 開発・運用コマンド
├── docker-compose.yml   # Neo4j環境設定
├── pyproject.toml       # Python設定（rye管理）
├── pytest.ini           # テスト設定
├── tmp/                  # 一時ファイル
├── logs/                 # 各種ログ
├── data/                 # dockercomposeのボリュームマウント
├── .claude/              # claude code設定
└── .qlty/                # qlty 設定
```

## 開発規約

### テスト駆動開発（TDD）

1. テストファーストで実装
2. レッドフェーズ → グリーンフェーズ → リファクタリング
3. カバレッジ目標: 80%以上

### コード品質

- qltyによる自動チェックを通過すること
- 型ヒントを必ず使用
- docstringでクラス・メソッドを文書化

#### 品質チェック除外事項

以下の警告は開発方針として許容する：

- `bandit:B101` - pytestでのassert使用（テストフレームワークの標準的な使用方法）
- `radarlint-python:python:S100` - テストメソッドの日本語命名（BDD仕様に従った命名）

### Git運用

- mainブランチへの直接プッシュは禁止
- 機能ブランチで開発し、PRでマージ
- コミットメッセージは日本語で簡潔に

## 環境構築手順

1. リポジトリのクローン
2. `rye sync` で依存関係インストール
3. `docker compose up -d` でNeo4j起動
4. `.env` ファイルの作成（`.env.example`を参考）

## よく使うコマンド

```bash
# フォーマット
qlty fmt

# テスト実行
rye run pytest

# カバレッジ確認
rye run pytest --cov=src --cov-report=html

# 品質チェック
qlty check
qlty smells
qlty metrics

# Neo4j起動/停止
docker compose up -d
docker compose down
```
