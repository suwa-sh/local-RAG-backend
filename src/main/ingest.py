"""ingest.py - ドキュメント登録のCLIエントリーポイント"""

import asyncio
import argparse
import sys
import logging

from src.domain.group_id import GroupId
from src.usecase.register_document_usecase import RegisterDocumentUseCase
from src.adapter.filesystem_document_reader import FileSystemDocumentReader
from src.adapter.unstructured_document_parser import UnstructuredDocumentParser
from src.adapter.graphiti_episode_repository import GraphitiEpisodeRepository
from src.adapter.chunk_file_manager import ChunkFileManager
from src.main.settings import load_config


def parse_arguments() -> argparse.Namespace:
    """
    コマンドライン引数をパースする

    Returns:
        argparse.Namespace: パース結果
    """
    parser = argparse.ArgumentParser(
        description="指定ディレクトリ配下のファイル群をナレッジ登録する"
    )
    parser.add_argument("directory", help="対象ディレクトリパス")
    parser.add_argument(
        "--workers", type=int, default=3, help="並列処理のワーカー数（デフォルト: 3）"
    )

    return parser.parse_args()


def create_usecase() -> RegisterDocumentUseCase:
    """
    RegisterDocumentUseCaseインスタンスを作成する

    Returns:
        RegisterDocumentUseCase: ユースケースインスタンス

    Raises:
        ValueError: 設定が不正な場合
    """
    # 環境変数から設定を読み込み
    config = load_config()

    # アダプターの初期化
    file_reader = FileSystemDocumentReader()

    document_parser = UnstructuredDocumentParser(
        max_characters=config.chunk.max_size,
        combine_text_under_n_chars=config.chunk.min_size,
        overlap=config.chunk.overlap,
    )

    # リポジトリの初期化
    episode_repository = GraphitiEpisodeRepository(
        neo4j_uri=config.neo4j.uri,
        neo4j_user=config.neo4j.user,
        neo4j_password=config.neo4j.password,
        llm_api_key=config.llm.key,
        llm_base_url=config.llm.url,
        llm_model=config.llm.name,
        rerank_model=config.llm.rerank_model,
        embedding_api_key=config.embedding.key,
        embedding_base_url=config.embedding.url,
        embedding_model=config.embedding.name,
    )

    # チャンクファイルマネージャーの初期化
    chunk_file_manager = ChunkFileManager()

    # ユースケースの作成
    return RegisterDocumentUseCase(
        file_reader=file_reader,
        document_parser=document_parser,
        episode_repository=episode_repository,
        chunk_file_manager=chunk_file_manager,
    )


def setup_logging(log_level: str = "INFO") -> None:
    """
    ログ設定を初期化する

    Args:
        log_level: ログレベル（DEBUG, INFO, WARNING, ERROR）
    """
    # 並列処理対応のログ設定を使用
    from src.adapter.logging_utils import setup_parallel_logging

    setup_parallel_logging(log_level)

    # API呼び出し分析に必要なopenaiログを有効化
    logging.getLogger("openai").setLevel(logging.DEBUG)

    # 最小限の外部ライブラリログ制御（特に問題のあるもののみ）
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("graphiti_core.utils.maintenance.edge_operations").setLevel(
        logging.ERROR
    )

    if log_level == "DEBUG":
        print("🔍 DEBUG モード（並列処理）でログを出力しています...")
    else:
        print(f"📊 {log_level} レベルでログを出力しています...")


async def main() -> int:
    """
    メイン処理

    Returns:
        int: 終了コード（0: 成功、1: 失敗）
    """
    try:
        # コマンドライン引数のパース
        args = parse_arguments()

        # 設定読み込み（環境変数から取得）
        config = load_config()

        # ログ設定の初期化（環境変数のログレベルを使用）
        setup_logging(config.logging.level)

        group_id = GroupId(config.group_id)

        # ユースケースの作成
        usecase = create_usecase()

        print(
            f"🚀 2段階並列処理モードで実行（チャンク: {args.workers}ワーカー, 登録: {config.parallel.register_workers}ワーカー）"
        )
        result = await usecase.execute(
            group_id,
            args.directory,
            chunking_workers=args.workers,
            register_workers=config.parallel.register_workers,
        )

        # 結果の表示
        if result.success:
            if result.total_files == 0:
                print("処理対象のファイルがありませんでした。")
            else:
                print("ドキュメント登録が正常に登録されました。")
                print(f"  処理ファイル数: {result.total_files}")
                print(f"  作成チャンク数: {result.total_chunks}")
                print(f"  登録エピソード数: {result.total_episodes}")
        else:
            print(f"登録に失敗しました: {result.error_message}")
            return 1

        return 0

    except FileNotFoundError as e:
        print(f"エラー: ディレクトリが見つかりません - {e}")
        return 1
    except ValueError as e:
        print(f"エラー: 設定が不正です - {e}")
        return 1
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        return 1
    finally:
        # GraphitiEpisodeRepositoryのクリーンアップは実装時に検討
        pass


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
