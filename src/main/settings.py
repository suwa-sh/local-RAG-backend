"""アプリケーション設定"""

import os
from dataclasses import dataclass


@dataclass
class Neo4jConfig:
    """Neo4j設定"""

    url: str
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
class RateLimitConfig:
    """Rate limit設定"""

    max_retries: int = 3
    default_wait_time: int = 121
    enable_coordinator: bool = True


@dataclass
class AppConfig:
    """アプリケーション設定"""

    neo4j: Neo4jConfig
    llm: LLMConfig
    embedding: EmbeddingConfig
    chunk: ChunkConfig
    rate_limit: RateLimitConfig
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
        "NEO4J_URL",
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
    llm_model_key = os.getenv("LLM_MODEL_KEY", "")
    if llm_model_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = llm_model_key

    # Neo4j設定
    neo4j_config = Neo4jConfig(
        url=os.getenv("NEO4J_URL", ""),
        user=os.getenv("NEO4J_USER", ""),
        password=os.getenv("NEO4J_PASSWORD", ""),
    )

    # LLM設定
    llm_config = LLMConfig(
        url=os.getenv("LLM_MODEL_URL", ""),
        name=os.getenv("LLM_MODEL_NAME", ""),
        key=os.getenv("LLM_MODEL_KEY", ""),
        rerank_model=os.getenv("RERANK_MODEL_NAME", os.getenv("LLM_MODEL_NAME", "")),
    )

    # 埋め込み設定
    embedding_config = EmbeddingConfig(
        url=os.getenv("EMBEDDING_MODEL_URL", ""),
        name=os.getenv("EMBEDDING_MODEL_NAME", ""),
        key=os.getenv("EMBEDDING_MODEL_KEY", ""),
    )

    # チャンク設定（オプション）
    chunk_config = ChunkConfig(
        max_size=int(os.getenv("CHUNK_SIZE_MAX", "1000")),
        min_size=int(os.getenv("CHUNK_SIZE_MIN", "100")),
        overlap=int(os.getenv("CHUNK_OVERLAP", "0")),
    )

    # Rate limit設定（オプション）
    rate_limit_config = RateLimitConfig(
        max_retries=int(os.getenv("INGEST_RATE_LIMIT_MAX_RETRIES", "3")),
        default_wait_time=int(os.getenv("INGEST_RATE_LIMIT_DEFAULT_WAIT_TIME", "121")),
        enable_coordinator=os.getenv(
            "INGEST_RATE_LIMIT_ENABLE_COORDINATOR", "true"
        ).lower()
        == "true",
    )

    return AppConfig(
        neo4j=neo4j_config,
        llm=llm_config,
        embedding=embedding_config,
        chunk=chunk_config,
        rate_limit=rate_limit_config,
        group_id=os.getenv("GROUP_ID", ""),
    )
