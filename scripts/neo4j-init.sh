#!/bin/bash
# Neo4j初期化スクリプト（Docker内で実行）

set -e

# 環境変数のデフォルト値設定
NEO4J_USER=${NEO4J_USER:-neo4j}
NEO4J_PASSWORD=${NEO4J_PASSWORD:-password}

echo "🔍 Neo4j初期化開始..."
echo "  ユーザー: $NEO4J_USER"

# Neo4jが完全に起動するまで待機
until cypher-shell -a bolt://neo4j:7687 -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "RETURN 1" > /dev/null 2>&1; do
    echo "⏳ Neo4jの起動を待機中..."
    sleep 5
done

echo "🔨 Graphiti用フルテキストインデックス作成中..."

# 初期化スクリプト実行
cypher-shell -a bolt://neo4j:7687 -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" -f /scripts/neo4j-init.cypher

echo "✅ Neo4j初期化完了"

# インデックス一覧表示
echo "📋 作成されたフルテキストインデックス:"
cypher-shell -a bolt://neo4j:7687 -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "
    SHOW FULLTEXT INDEXES
    YIELD name, state, entityType, labelsOrTypes
    RETURN name, state, entityType, labelsOrTypes
    ORDER BY name
"