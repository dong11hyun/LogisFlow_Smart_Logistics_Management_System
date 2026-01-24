"""
Q4 벤치마크: PostgreSQL 파티션 vs Elasticsearch 조회 성능 비교

사용법:
1. 서버 실행: uvicorn app.main:app --reload --port 8000
2. 벤치마크 실행: python scripts/benchmark_q4.py
"""

import requests
import time
import statistics
import concurrent.futures
import random

# 설정
API_URL = "http://localhost:8000"
TOTAL_REQUESTS = 200  # 전략당 요청 횟수
CONCURRENCY = 20      # 동시 요청 수


def send_timeline_request(shipment_id: int, source: str):
    """타임라인 조회 API 요청"""
    start_time = time.time()
    try:
        resp = requests.get(
            f"{API_URL}/shipments/{shipment_id}/timeline",
            params={"source": source}
        )
        resp.raise_for_status()
        data = resp.json()
        latency = (time.time() - start_time) * 1000  # 클라이언트 측 ms
        server_time = data.get("query_time_ms", 0)  # 서버 측 처리 시간
        total_updates = data.get("total_updates", 0)
        return latency, server_time, total_updates, True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # 화물이 없는 경우 무시
            return 0, 0, 0, False
        print(f"❌ Error ({source}): {e}")
        return 0, 0, 0, False
    except Exception as e:
        print(f"❌ Error ({source}): {e}")
        return 0, 0, 0, False


def run_benchmark(source: str):
    """특정 소스 벤치마크 실행"""
    print(f"\n🚀 Benchmarking Source: {source} ...")
    
    latencies = []
    server_times = []
    update_counts = []
    success_count = 0
    
    # 1~1억 범위의 랜덤 화물 ID (1억 건 테스트용)
    shipment_ids = [random.randint(1, 3000000) for _ in range(TOTAL_REQUESTS)]
    
    start_total = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(send_timeline_request, sid, source) for sid in shipment_ids]
        
        for future in concurrent.futures.as_completed(futures):
            latency, server_time, updates, success = future.result()
            if success:
                latencies.append(latency)
                server_times.append(server_time)
                update_counts.append(updates)
                success_count += 1
                
    total_time = time.time() - start_total
    
    if success_count == 0:
        print(f"⚠️ No successful requests for {source}")
        return {
            "source": source,
            "tps": 0,
            "avg_latency": 0,
            "avg_server": 0,
            "p99_server": 0,
            "avg_updates": 0
        }
    
    tps = success_count / total_time
    avg_latency = statistics.mean(latencies)
    avg_server = statistics.mean(server_times)
    avg_updates = statistics.mean(update_counts)
    
    print(f"✅ Completed {success_count}/{TOTAL_REQUESTS} requests in {total_time:.2f}s")
    print(f"📊 TPS: {tps:.2f}")
    print(f"⏱️ Avg Client Latency: {avg_latency:.2f} ms")
    print(f"🖥️ Avg Server Time: {avg_server:.2f} ms")
    print(f"📋 Avg Updates per Shipment: {avg_updates:.1f}")
    
    return {
        "source": source,
        "tps": tps,
        "avg_latency": avg_latency,
        "avg_server": avg_server,
        "p99_server": statistics.quantiles(server_times, n=100)[98] if len(server_times) >= 100 else max(server_times) if server_times else 0,
        "avg_updates": avg_updates
    }


if __name__ == "__main__":
    print(f"🔥 Starting Q4 Benchmark (Requests: {TOTAL_REQUESTS}, Concurrency: {CONCURRENCY})")
    print("=" * 70)
    
    results = []
    
    # 방안 1: PostgreSQL 파티션 테이블
    results.append(run_benchmark("postgresql"))
    
    # 방안 2: Elasticsearch
    results.append(run_benchmark("elasticsearch"))
    
    print("\n" + "=" * 85)
    print("🏆 FINAL RESULTS - Q4 저장소 비교")
    print("=" * 85)
    print(f"{'Source':<15} | {'TPS':<8} | {'Client Avg':<12} | {'Server Avg':<12} | {'Server P99':<12}")
    print("-" * 85)
    
    for r in results:
        print(f"{r['source']:<15} | {r['tps']:<8.2f} | {r['avg_latency']:<12.2f} | {r['avg_server']:<12.2f} | {r['p99_server']:<12.2f}")
    
    print("\n💡 Client Avg = HTTP 왕복 시간 (네트워크 포함)")
    print("💡 Server Avg = 순수 서버 조회 시간 (API 내부)")
    
    # 비교 분석
    if len(results) == 2 and results[0]["avg_server"] > 0 and results[1]["avg_server"] > 0:
        pg_time = results[0]["avg_server"]
        es_time = results[1]["avg_server"]
        
        if es_time < pg_time:
            improvement = ((pg_time - es_time) / pg_time) * 100
            print(f"\n📈 Elasticsearch가 PostgreSQL보다 {improvement:.1f}% 빠름!")
        else:
            improvement = ((es_time - pg_time) / es_time) * 100
            print(f"\n📈 PostgreSQL이 Elasticsearch보다 {improvement:.1f}% 빠름!")
