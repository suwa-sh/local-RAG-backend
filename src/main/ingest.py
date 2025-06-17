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

    # ユースケースの作成
    return RegisterDocumentUseCase(
        file_reader=file_reader,
        document_parser=document_parser,
        episode_repository=episode_repository,
    )


def setup_logging() -> None:
    """
    ログ設定を初期化する
    """
    # 並列処理対応のログ設定を使用
    from src.adapter.logging_utils import setup_parallel_logging

    setup_parallel_logging()

    # 外部ライブラリのログレベルを調整
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)  # Neo4j警告を抑制
    logging.getLogger("unstructured").setLevel(logging.WARNING)
    logging.getLogger("unstructured.trace").setLevel(logging.WARNING)

    # Graphitiライブラリのログをプロダクション向けに調整
    logging.getLogger("graphiti_core").setLevel(logging.INFO)
    logging.getLogger("graphiti_core.utils.maintenance.edge_operations").setLevel(
        logging.ERROR
    )  # 日付パース警告を抑制
    # DEBUGログを無効化してパフォーマンス向上
    logging.getLogger("src.usecase.register_document_usecase").setLevel(logging.INFO)
    logging.getLogger("src.adapter.graphiti_episode_repository").setLevel(logging.INFO)

    print("🔍 DEBUG モード（並列処理）でログを出力しています...")


async def main() -> int:
    """
    メイン処理

    Returns:
        int: 終了コード（0: 成功、1: 失敗）
    """
    try:
        # コマンドライン引数のパース
        args = parse_arguments()

        # ログ設定の初期化
        setup_logging()

        # 設定読み込み（GROUP_ID環境変数から取得）
        config = load_config()
        group_id = GroupId(config.group_id)

        # ユースケースの作成
        usecase = create_usecase()

        print(f"🚀 並列処理モードで実行（ワーカー数: {args.workers}）")
        result = await usecase.execute_parallel(
            group_id, args.directory, max_workers=args.workers
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
