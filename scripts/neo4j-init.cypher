// Neo4j初期化スクリプト
// Graphitiライブラリが必要とするフルテキストインデックスを作成

// エンティティノード用フルテキストインデックス
CREATE FULLTEXT INDEX node_name_and_summary IF NOT EXISTS 
FOR (n:Entity) ON EACH [n.name, n.summary];

// リレーションシップ用フルテキストインデックス  
CREATE FULLTEXT INDEX edge_name_and_summary IF NOT EXISTS 
FOR ()-[r:RELATES_TO]-() ON EACH [r.name, r.summary];

// エピソードノード用フルテキストインデックス
CREATE FULLTEXT INDEX episodic_content IF NOT EXISTS 
FOR (n:Episodic) ON EACH [n.content, n.name];