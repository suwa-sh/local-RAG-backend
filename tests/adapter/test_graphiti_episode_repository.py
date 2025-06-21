"""GraphitiEpisodeRepositoryのテスト"""

import pytest

from src.adapter.graphiti_episode_repository import GraphitiEpisodeRepository


class TestGraphitiEpisodeRepository:
    """GraphitiEpisodeRepositoryのテスト"""

    @pytest.mark.skipif(
        True, reason="Graphitiクライアント初期化にはOPENAI_API_KEY環境変数が必要"
    )
    def test_GraphitiEpisodeRepository作成_基本動作確認(self):
        """GraphitiEpisodeRepositoryの基本動作確認（スキップ）"""
        pass

    # 削除されたメソッドに依存するテストをコメントアウト
    # 未使用メソッド削除により以下のメソッドは利用不可:
    # save_batch, close

    def test_削除されたメソッドに依存するテスト_スキップ(self):
        """削除されたメソッドに依存するテストはスキップ"""
        pass
