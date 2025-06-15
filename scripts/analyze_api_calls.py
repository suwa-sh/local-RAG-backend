#!/usr/bin/env python3
"""
API呼び出し分析スクリプト。LLMとEmbeddingの呼び出し回数と処理時間を抽出する
"""

import re
import sys
from datetime import datetime
from collections import defaultdict

# 定数定義
ERROR_PREFIX = "❌ ファイル処理失敗:"


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
    retry_events = []
    processing_summary = {}

    # リクエスト開始時刻を記録
    pending_llm = {}
    pending_embedding = {}

    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                # 時刻を抽出
                time_match = re.match(r"^(\d{2}:\d{2}:\d{2})", line)

                # 時刻あり行の処理
                if time_match:
                    time_str = time_match.group(1)
                    time_obj = parse_time(time_str)
                    if not time_obj:
                        continue

                    # スレッドIDとファイル名を抽出 [T123][filename]
                    thread_match = re.search(r"\[T(\d+)\]\[([^\]]+)\]", line)
                    thread_id = thread_match.group(1) if thread_match else "unknown"
                    file_name = thread_match.group(2) if thread_match else "unknown"
                else:
                    # 時刻なし行でも処理サマリーは解析
                    time_obj = None
                    thread_id = "main"
                    file_name = "main"

                # LLM リクエスト開始（時刻がある場合のみ）
                if (
                    time_obj
                    and "Sending HTTP Request: POST" in line
                    and "chat/completions" in line
                ):
                    key = f"{thread_id}_{file_name}"
                    pending_llm[key] = {
                        "start_time": time_obj,
                        "line_num": line_num,
                        "thread_id": thread_id,
                        "file_name": file_name,
                    }

                # LLM レスポンス（時刻がある場合のみ）
                elif (
                    time_obj
                    and "HTTP Response: POST" in line
                    and "chat/completions" in line
                ):
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

                # Embedding リクエスト開始（時刻がある場合のみ）
                elif (
                    time_obj
                    and "Sending HTTP Request: POST" in line
                    and "embeddings" in line
                ):
                    key = f"{thread_id}_{file_name}_{time_obj.timestamp()}"  # 同時並行のため時刻も含める
                    pending_embedding[key] = {
                        "start_time": time_obj,
                        "line_num": line_num,
                        "thread_id": thread_id,
                        "file_name": file_name,
                    }

                # Embedding レスポンス（時刻がある場合のみ）
                elif (
                    time_obj and "HTTP Response: POST" in line and "embeddings" in line
                ):
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

                # Rate limitリトライの検出（時刻がある場合のみ）
                elif time_obj and "🔄 Rate limit detected" in line:
                    # 例: 🔄 Rate limit detected. Waiting 61 seconds before retry (rate limit attempt 1/3)
                    wait_match = re.search(r"Waiting (\d+) seconds", line)
                    attempt_match = re.search(r"attempt (\d+)/(\d+)", line)

                    wait_time = int(wait_match.group(1)) if wait_match else 0
                    current_attempt = (
                        int(attempt_match.group(1)) if attempt_match else 0
                    )
                    max_attempts = int(attempt_match.group(2)) if attempt_match else 0

                    retry_events.append(
                        {
                            "type": "rate_limit",
                            "time": time_obj,
                            "file_name": file_name,
                            "wait_time": wait_time,
                            "attempt": current_attempt,
                            "max_attempts": max_attempts,
                            "line_num": line_num,
                        }
                    )

                # IndexErrorリトライの検出（時刻がある場合のみ）
                elif time_obj and "⚠️ Graphitiエンティティ競合エラー" in line:
                    # 例: ⚠️ Graphitiエンティティ競合エラー。1秒後にリトライ (index error attempt 1/3)
                    wait_match = re.search(r"(\d+)秒後にリトライ", line)
                    attempt_match = re.search(r"attempt (\d+)/(\d+)", line)

                    wait_time = int(wait_match.group(1)) if wait_match else 0
                    current_attempt = (
                        int(attempt_match.group(1)) if attempt_match else 0
                    )
                    max_attempts = int(attempt_match.group(2)) if attempt_match else 0

                    retry_events.append(
                        {
                            "type": "index_error",
                            "time": time_obj,
                            "file_name": file_name,
                            "wait_time": wait_time,
                            "attempt": current_attempt,
                            "max_attempts": max_attempts,
                            "line_num": line_num,
                        }
                    )

                # 最終処理結果の検出
                elif "ドキュメント登録が正常に登録されました" in line:
                    # 後続の処理結果行を探す
                    pass
                elif "処理ファイル数:" in line:
                    file_count_match = re.search(r"処理ファイル数: (\d+)", line)
                    if file_count_match:
                        processing_summary["total_files"] = int(
                            file_count_match.group(1)
                        )
                elif "作成チャンク数:" in line:
                    chunk_count_match = re.search(r"作成チャンク数: (\d+)", line)
                    if chunk_count_match:
                        processing_summary["total_chunks"] = int(
                            chunk_count_match.group(1)
                        )
                elif "登録エピソード数:" in line:
                    episode_count_match = re.search(r"登録エピソード数: (\d+)", line)
                    if episode_count_match:
                        processing_summary["total_episodes"] = int(
                            episode_count_match.group(1)
                        )
                elif "⚠️ 処理失敗ファイル数:" in line:
                    failed_count_match = re.search(r"処理失敗ファイル数: (\d+)", line)
                    if failed_count_match:
                        processing_summary["failed_files"] = int(
                            failed_count_match.group(1)
                        )

                # 失敗ファイルの詳細を収集（時刻がある場合のみ）
                elif time_obj and "❌ ファイル処理失敗:" in line:
                    # 例: ❌ ファイル処理失敗: /data/input/SRv6-IaaS/ADR/images/tag_model.png - libGL.so.1: cannot open shared object file
                    file_match = re.search(r"❌ ファイル処理失敗: ([^-]+) - (.+)", line)
                    if file_match:
                        file_path = file_match.group(1).strip()
                        error_message = file_match.group(2).strip()

                        if "failed_file_details" not in processing_summary:
                            processing_summary["failed_file_details"] = []

                        processing_summary["failed_file_details"].append(
                            {
                                "file_path": file_path,
                                "error_message": error_message,
                                "time": time_obj,
                                "line_num": line_num,
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
        "retry_events": retry_events,
        "processing_summary": processing_summary,
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

    # リトライ分析
    retry_events = analysis_result.get("retry_events", [])
    if retry_events:
        print("\n🔄 リトライ分析")

        # Rate limitリトライ
        rate_limit_retries = [r for r in retry_events if r["type"] == "rate_limit"]
        if rate_limit_retries:
            print(f"  📊 Rate Limitリトライ: {len(rate_limit_retries)}回")

            wait_times = [r["wait_time"] for r in rate_limit_retries]
            if wait_times:
                avg_wait = sum(wait_times) / len(wait_times)
                total_wait = sum(wait_times)
                max_wait = max(wait_times)
                min_wait = min(wait_times)

                print(f"    平均待機時間: {avg_wait:.1f}秒")
                print(f"    最大待機時間: {max_wait}秒")
                print(f"    最小待機時間: {min_wait}秒")
                print(f"    総待機時間: {total_wait}秒")

                # ファイル別リトライ統計
                file_retries = defaultdict(list)
                for retry in rate_limit_retries:
                    file_retries[retry["file_name"]].append(retry["wait_time"])

                print("\n    📁 ファイル別Rate Limitリトライ:")
                for file_name, wait_times in file_retries.items():
                    count = len(wait_times)
                    avg = sum(wait_times) / len(wait_times)
                    total = sum(wait_times)
                    print(
                        f"      {file_name}: {count}回, 平均{avg:.1f}秒, 合計{total}秒"
                    )

        # IndexErrorリトライ
        index_error_retries = [r for r in retry_events if r["type"] == "index_error"]
        if index_error_retries:
            print(f"\n  ⚠️ IndexErrorリトライ: {len(index_error_retries)}回")

            wait_times = [r["wait_time"] for r in index_error_retries]
            if wait_times:
                total_wait = sum(wait_times)
                print(f"    総待機時間: {total_wait}秒")

                # ファイル別統計
                file_retries = defaultdict(int)
                for retry in index_error_retries:
                    file_retries[retry["file_name"]] += 1

                print("    📁 ファイル別IndexErrorリトライ:")
                for file_name, count in file_retries.items():
                    print(f"      {file_name}: {count}回")

    # 処理サマリー
    processing_summary = analysis_result.get("processing_summary", {})
    if processing_summary:
        print("\n📋 処理サマリー")

        if "total_files" in processing_summary:
            print(f"  📁 処理ファイル数: {processing_summary['total_files']}件")

        if "total_chunks" in processing_summary:
            print(f"  🔀 作成チャンク数: {processing_summary['total_chunks']}件")

        if "total_episodes" in processing_summary:
            print(f"  📝 登録エピソード数: {processing_summary['total_episodes']}件")

        if "failed_files" in processing_summary:
            print(f"  ❌ 処理失敗ファイル数: {processing_summary['failed_files']}件")

            # 失敗ファイルの詳細表示
            if "failed_file_details" in processing_summary:
                print("\n    📄 失敗ファイル詳細:")
                for i, failure in enumerate(
                    processing_summary["failed_file_details"], 1
                ):
                    file_name = failure["file_path"].split("/")[
                        -1
                    ]  # ファイル名のみ抽出
                    print(f"      {i}. {file_name}")
                    print(f"         パス: {failure['file_path']}")
                    print(f"         エラー: {failure['error_message']}")

            # 成功率計算
            if "total_files" in processing_summary:
                total = processing_summary["total_files"]
                failed = processing_summary["failed_files"]
                success_rate = ((total - failed) / total) * 100 if total > 0 else 0
                print(f"  ✅ 成功率: {success_rate:.1f}% ({total - failed}/{total})")

    # 総合分析
    if llm_requests and embedding_requests and retry_events:
        print("\n🎯 総合分析")

        # API処理時間
        llm_total = sum(req["duration"] for req in llm_requests)
        embedding_total = sum(req["duration"] for req in embedding_requests)
        api_total = llm_total + embedding_total

        # リトライ待機時間
        retry_total = sum(r["wait_time"] for r in retry_events)

        # 全体時間に対する比率
        if api_total > 0:
            retry_ratio = (retry_total / api_total) * 100
            print(f"  ⏱️ API処理時間: {api_total:.0f}秒")
            print(f"  ⏳ リトライ待機時間: {retry_total}秒")
            print(f"  📈 リトライ時間比率: {retry_ratio:.1f}%")

        # リトライ効果
        rate_limit_count = len([r for r in retry_events if r["type"] == "rate_limit"])
        if rate_limit_count > 0:
            print(f"  🛡️ Rate Limitリトライによる回復: {rate_limit_count}回")


def print_failed_files(log_file_path):
    """失敗ファイルの詳細を表示"""
    try:
        failed_files = []
        with open(log_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if ERROR_PREFIX in line:
                    failed_files.append(line.strip())

        if failed_files:
            print(f"\n📄 失敗ファイル詳細: {len(failed_files)}件")
            for i, line in enumerate(failed_files, 1):
                # ログ行から情報を抽出
                # 例: 02:42:28 [T184][tag_model] - src.usecase.register_document_usecase - ERROR - ❌ ファイル処理失敗: /data/input/.../file.png - error message
                if ERROR_PREFIX in line:
                    # ファイルパスとエラーメッセージを抽出
                    parts = line.split(ERROR_PREFIX)
                    if len(parts) > 1:
                        file_and_error = parts[1].strip()
                        if " - " in file_and_error:
                            file_path, error_msg = file_and_error.split(" - ", 1)
                            file_name = file_path.strip().split("/")[
                                -1
                            ]  # ファイル名のみ
                            print(f"  {i}. {file_name}")
                            print(f"     パス: {file_path.strip()}")
                            print(f"     エラー: {error_msg.strip()}")
    except Exception as e:
        print(f"失敗ファイル詳細の取得中にエラー: {e}")


def main():
    """メイン関数"""
    if len(sys.argv) != 2:
        print("使用方法: python analyze_api_calls.py <ログファイルパス>")
        print("例: python tmp/analyze_api_calls.py tmp/ingest-example-parallel.log")
        sys.exit(1)

    log_file_path = sys.argv[1]

    print(f"📊 ログファイル分析中: {log_file_path}")

    analysis_result = analyze_log_file(log_file_path)
    print_statistics(analysis_result)

    # 失敗ファイルの詳細を表示
    print_failed_files(log_file_path)


if __name__ == "__main__":
    main()
