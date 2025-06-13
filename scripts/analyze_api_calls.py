#!/usr/bin/env python3
"""
API呼び出し分析スクリプト。LLMとEmbeddingの呼び出し回数と処理時間を抽出する
"""

import re
import sys
from datetime import datetime
from collections import defaultdict


def parse_time(time_str):
    """時刻文字列をdatetimeオブジェクトに変換"""
    try:
        # HH:MM:SS形式
        time_obj = datetime.strptime(time_str, "%H:%M:%S")
        return time_obj
    except ValueError:
        return None


def analyze_log_file(log_file_path):
    """ログファイルを分析してAPI呼び出し統計を生成"""

    llm_requests = []
    embedding_requests = []

    # リクエスト開始時刻を記録
    pending_llm = {}
    pending_embedding = {}

    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                # 時刻を抽出
                time_match = re.match(r"^(\d{2}:\d{2}:\d{2})", line)
                if not time_match:
                    continue

                time_str = time_match.group(1)
                time_obj = parse_time(time_str)
                if not time_obj:
                    continue

                # スレッドIDとファイル名を抽出 [T123][filename]
                thread_match = re.search(r"\[T(\d+)\]\[([^\]]+)\]", line)
                thread_id = thread_match.group(1) if thread_match else "unknown"
                file_name = thread_match.group(2) if thread_match else "unknown"

                # LLM リクエスト開始
                if "Sending HTTP Request: POST" in line and "chat/completions" in line:
                    key = f"{thread_id}_{file_name}"
                    pending_llm[key] = {
                        "start_time": time_obj,
                        "line_num": line_num,
                        "thread_id": thread_id,
                        "file_name": file_name,
                    }

                # LLM レスポンス
                elif "HTTP Response: POST" in line and "chat/completions" in line:
                    key = f"{thread_id}_{file_name}"
                    if key in pending_llm:
                        start_info = pending_llm.pop(key)
                        duration = (time_obj - start_info["start_time"]).total_seconds()
                        llm_requests.append(
                            {
                                "thread_id": thread_id,
                                "file_name": file_name,
                                "start_time": start_info["start_time"],
                                "end_time": time_obj,
                                "duration": duration,
                                "start_line": start_info["line_num"],
                                "end_line": line_num,
                            }
                        )

                # Embedding リクエスト開始
                elif "Sending HTTP Request: POST" in line and "embeddings" in line:
                    key = f"{thread_id}_{file_name}_{time_obj.timestamp()}"  # 同時並行のため時刻も含める
                    pending_embedding[key] = {
                        "start_time": time_obj,
                        "line_num": line_num,
                        "thread_id": thread_id,
                        "file_name": file_name,
                    }

                # Embedding レスポンス
                elif "HTTP Response: POST" in line and "embeddings" in line:
                    # 最も近い開始時刻のリクエストとマッチング
                    matching_key = None
                    min_diff = float("inf")

                    for key, start_info in pending_embedding.items():
                        if (
                            start_info["thread_id"] == thread_id
                            and start_info["file_name"] == file_name
                        ):
                            diff = abs(
                                (time_obj - start_info["start_time"]).total_seconds()
                            )
                            if diff < min_diff:
                                min_diff = diff
                                matching_key = key

                    if matching_key:
                        start_info = pending_embedding.pop(matching_key)
                        duration = (time_obj - start_info["start_time"]).total_seconds()
                        embedding_requests.append(
                            {
                                "thread_id": thread_id,
                                "file_name": file_name,
                                "start_time": start_info["start_time"],
                                "end_time": time_obj,
                                "duration": duration,
                                "start_line": start_info["line_num"],
                                "end_line": line_num,
                            }
                        )

    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {log_file_path}")
        return None
    except Exception as e:
        print(f"エラー: ログファイル解析中にエラーが発生: {e}")
        return None

    return {
        "llm_requests": llm_requests,
        "embedding_requests": embedding_requests,
        "pending_llm": pending_llm,
        "pending_embedding": pending_embedding,
    }


def print_statistics(analysis_result):
    """統計情報を出力"""
    if not analysis_result:
        return

    llm_requests = analysis_result["llm_requests"]
    embedding_requests = analysis_result["embedding_requests"]

    print("=" * 80)
    print("API呼び出し分析結果")
    print("=" * 80)

    # LLM統計
    print("\n🤖 LLM API呼び出し (chat/completions)")
    print(f"  総呼び出し回数: {len(llm_requests)}")

    if llm_requests:
        durations = [req["duration"] for req in llm_requests]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        total_duration = sum(durations)

        print(f"  平均処理時間: {avg_duration:.2f}秒")
        print(f"  最大処理時間: {max_duration:.2f}秒")
        print(f"  最小処理時間: {min_duration:.2f}秒")
        print(f"  総処理時間: {total_duration:.2f}秒")

        # ファイル別統計
        file_stats = defaultdict(list)
        for req in llm_requests:
            file_stats[req["file_name"]].append(req["duration"])

        print("\n  📁 ファイル別LLM呼び出し:")
        for file_name, durations in file_stats.items():
            count = len(durations)
            avg = sum(durations) / len(durations)
            total = sum(durations)
            print(f"    {file_name}: {count}回, 平均{avg:.2f}秒, 合計{total:.2f}秒")

    # Embedding統計
    print("\n🔤 Embedding API呼び出し (/embeddings)")
    print(f"  総呼び出し回数: {len(embedding_requests)}")

    if embedding_requests:
        durations = [req["duration"] for req in embedding_requests]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        total_duration = sum(durations)

        print(f"  平均処理時間: {avg_duration:.2f}秒")
        print(f"  最大処理時間: {max_duration:.2f}秒")
        print(f"  最小処理時間: {min_duration:.2f}秒")
        print(f"  総処理時間: {total_duration:.2f}秒")

        # ファイル別統計
        file_stats = defaultdict(list)
        for req in embedding_requests:
            file_stats[req["file_name"]].append(req["duration"])

        print("\n  📁 ファイル別Embedding呼び出し:")
        for file_name, durations in file_stats.items():
            count = len(durations)
            avg = sum(durations) / len(durations)
            total = sum(durations)
            print(f"    {file_name}: {count}回, 平均{avg:.2f}秒, 合計{total:.2f}秒")

    # 比較分析
    print("\n📊 比較分析")
    if llm_requests and embedding_requests:
        llm_total = sum(req["duration"] for req in llm_requests)
        embedding_total = sum(req["duration"] for req in embedding_requests)
        grand_total = llm_total + embedding_total

        llm_percentage = (llm_total / grand_total) * 100
        embedding_percentage = (embedding_total / grand_total) * 100

        print(f"  LLM処理時間割合: {llm_percentage:.1f}% ({llm_total:.2f}秒)")
        print(
            f"  Embedding処理時間割合: {embedding_percentage:.1f}% ({embedding_total:.2f}秒)"
        )
        print(f"  API呼び出し総時間: {grand_total:.2f}秒")

    # 未完了リクエスト警告
    pending_llm = analysis_result["pending_llm"]
    pending_embedding = analysis_result["pending_embedding"]

    if pending_llm:
        print(f"\n⚠️  未完了LLMリクエスト: {len(pending_llm)}件")
        for key, info in pending_llm.items():
            print(f"    {info['file_name']} (line {info['line_num']})")

    if pending_embedding:
        print(f"\n⚠️  未完了Embeddingリクエスト: {len(pending_embedding)}件")
        for key, info in pending_embedding.items():
            print(f"    {info['file_name']} (line {info['line_num']})")


def main():
    """メイン関数"""
    if len(sys.argv) != 2:
        print("使用方法: python analyze_api_calls.py <ログファイルパス>")
        print("例: python tmp/analyze_api_calls.py tmp/ingest-example-parallel.log")
        sys.exit(1)

    log_file_path = sys.argv[1]

    print(f"📊 ログファイル分析中: {log_file_path}")
    print("これには少し時間がかかる場合があります...")

    analysis_result = analyze_log_file(log_file_path)
    print_statistics(analysis_result)


if __name__ == "__main__":
    main()
