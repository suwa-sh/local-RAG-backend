"""アプリケーション設定"""

import os
from dataclasses import dataclass


@dataclass
class Neo4jConfig:
    """Neo4j設定"""

    uri: str
    user: str
    password: str


@dataclass
class LLMConfig:
    """LLM設定"""

    url: str
    name: str
    key: str
    rerank_model: str


@dataclass
class EmbeddingConfig:
    """埋め込み設定"""

    url: str
    name: str
    key: str


@dataclass
class ChunkConfig:
    """チャンク設定"""

    max_size: int = 2000
    min_size: int = 200
    overlap: int = 0


@dataclass
class LoggingConfig:
    """ログ設定"""

    level: str = "INFO"


@dataclass
class ParallelConfig:
    """並列処理設定"""

    chunk_workers: int = 3
    register_workers: int = 2


@dataclass
class AppConfig:
    """アプリケーション設定"""

    neo4j: Neo4jConfig
    llm: LLMConfig
    embedding: EmbeddingConfig
    chunk: ChunkConfig
    logging: LoggingConfig
    parallel: ParallelConfig
    group_id: str


def load_config() -> AppConfig:
    """
    環境変数からアプリケーション設定を読み込む

    Returns:
        AppConfig: アプリケーション設定

    Raises:
        ValueError: 必須の環境変数が設定されていない場合
    """
    # 必須環境変数のチェック
    required_vars = [
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_PASSWORD",
        "LLM_MODEL_URL",
        "LLM_MODEL_NAME",
        "LLM_MODEL_KEY",
        "EMBEDDING_MODEL_URL",
        "EMBEDDING_MODEL_NAME",
        "EMBEDDING_MODEL_KEY",
        "GROUP_ID",
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        raise ValueError(
            f"必須の環境変数が設定されていません: {', '.join(missing_vars)}"
        )

    # GraphitiライブラリがOPENAI_API_KEYを要求するため、LLM_MODEL_KEYと同じ値を設定
    llm_model_key = os.getenv("LLM_MODEL_KEY")
    if llm_model_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = llm_model_key

    # Neo4j設定
    neo4j_config = Neo4jConfig(
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
    )

    # LLM設定
    llm_config = LLMConfig(
        url=os.getenv("LLM_MODEL_URL"),
        name=os.getenv("LLM_MODEL_NAME"),
        key=os.getenv("LLM_MODEL_KEY"),
        rerank_model=os.getenv("RERANK_MODEL_NAME", os.getenv("LLM_MODEL_NAME")),
    )

    # 埋め込み設定
    embedding_config = EmbeddingConfig(
        url=os.getenv("EMBEDDING_MODEL_URL"),
        name=os.getenv("EMBEDDING_MODEL_NAME"),
        key=os.getenv("EMBEDDING_MODEL_KEY"),
    )

    # チャンク設定（オプション）
    chunk_config = ChunkConfig(
        max_size=int(os.getenv("CHUNK_SIZE_MAX", "1000")),
        min_size=int(os.getenv("CHUNK_SIZE_MIN", "100")),
        overlap=int(os.getenv("CHUNK_OVERLAP", "0")),
    )

    # ログ設定（オプション）
    logging_config = LoggingConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())

    # 並列処理設定（オプション）
    parallel_config = ParallelConfig(
        chunk_workers=int(os.getenv("INGEST_CHUNK_WORKERS", "3")),
        register_workers=int(os.getenv("INGEST_REGISTER_WORKERS", "1")),
    )

    return AppConfig(
        neo4j=neo4j_config,
        llm=llm_config,
        embedding=embedding_config,
        chunk=chunk_config,
        logging=logging_config,
        parallel=parallel_config,
        group_id=os.getenv("GROUP_ID"),
    )
