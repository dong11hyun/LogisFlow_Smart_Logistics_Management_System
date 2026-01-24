import requests
import time
import statistics
import concurrent.futures
import random
import psycopg2

# 설정
API_URL = "http://localhost:8000"
TOTAL_REQUESTS = 500  # 전략당 요청 횟수
CONCURRENCY = 30      # 동시 요청 수

# PostgreSQL 연결 (트리거 제어용)
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'user': 'postgres',
    'password': 'logisflow1234',
    'dbname': 'logisflow'
}


def set_trigger_state(enabled: bool):
    """
    트리거 상태 제어
    
    - enabled=True: 트리거 활성화 (trigger 전략용)
    - enabled=False: 트리거 비활성화 (sync, async 전략용)
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    action = "ENABLE" if enabled else "DISABLE"
    cur.execute(f"ALTER TABLE shipment_updates {action} TRIGGER ALL;")
    
    conn.commit()
    cur.close()
    conn.close()
    
    status = "활성화 ✅" if enabled else "비활성화 ❌"
    print(f"   🔔 트리거 {status}")


def send_request(shipment_id, strategy):
    """API 요청 전송"""
    status_codes = ["PENDING", "PICKED_UP", "IN_TRANSIT", "OUT_DELIVERY", "DELIVERED"]
    payload = {
        "status_code": random.choice(status_codes),
        "notes": f"Benchmark {strategy}",
        "strategy": strategy
    }
    
    start_time = time.time()
    try:
        resp = requests.post(f"{API_URL}/shipments/{shipment_id}/status", json=payload)
        resp.raise_for_status()
        data = resp.json()
        latency = (time.time() - start_time) * 1000  # 클라이언트측 latency (ms)
        server_time = data.get("processing_time_ms", 0)  # 서버측 처리 시간
        return latency, server_time, True
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0, 0, False

def run_benchmark(strategy):
    """특정 전략 벤치마크 실행"""
    print(f"\n🚀 Benchmarking Strategy: {strategy} ...")
    
    # 📌 전략별 트리거 상태 설정 (공정한 비교!)
    if strategy == "trigger":
        set_trigger_state(enabled=True)   # trigger 전략은 트리거 ON
    else:
        set_trigger_state(enabled=False)  # sync, async 등은 트리거 OFF
    
    latencies = []
    server_times = []
    success_count = 0
    
    # 1~1천만번 화물에 대해 테스트 (1천만 건 데이터)
    shipment_ids = [random.randint(1, 3000000) for _ in range(TOTAL_REQUESTS)]
    
    start_total = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(send_request, sid, strategy) for sid in shipment_ids]
        
        for future in concurrent.futures.as_completed(futures):
            latency, server_time, success = future.result()
            if success:
                latencies.append(latency)
                server_times.append(server_time)
                success_count += 1
                
    total_time = time.time() - start_total
    tps = success_count / total_time
    
    avg_latency = statistics.mean(latencies) if latencies else 0
    avg_server = statistics.mean(server_times) if server_times else 0
    
    print(f"✅ Completed {success_count}/{TOTAL_REQUESTS} requests in {total_time:.2f}s")
    print(f"📊 TPS: {tps:.2f}")
    print(f"⏱️ Avg Client Latency: {avg_latency:.2f} ms")
    print(f"🖥️ Avg Server Time: {avg_server:.2f} ms")
    
    return {
        "strategy": strategy,
        "tps": tps,
        "avg_latency": avg_latency,
        "p99_latency": statistics.quantiles(latencies, n=100)[98] if latencies else 0,
        "avg_server": avg_server,
        "p99_server": statistics.quantiles(server_times, n=100)[98] if server_times else 0
    }

if __name__ == "__main__":
    print(f"🔥 Starting Q3 Benchmark (Requests: {TOTAL_REQUESTS}, Concurrency: {CONCURRENCY})")
    print("📌 트리거 자동 제어: trigger 전략만 ON, 나머지는 OFF")
    
    results = []
    
    # 전략 1: Sync (트리거 OFF)
    results.append(run_benchmark("sync"))
    
    # 전략 2: Trigger (트리거 ON)
    results.append(run_benchmark("trigger"))
    
    # 전략 3: Async (트리거 OFF + Kafka)
    results.append(run_benchmark("async"))
    
    # 전략 4: Async Pure (트리거 OFF + Kafka만)
    results.append(run_benchmark("async_pure"))
    
    # 전략 5: Async Fire (트리거 OFF + Kafka만, SELECT도 없음!)
    results.append(run_benchmark("async_fire"))
    
    # 벤치마크 완료 후 트리거 원복
    set_trigger_state(enabled=True)
    print("\n   🔔 벤치마크 완료, 트리거 원복 (활성화)")
    
    print("\n" + "=" * 85)
    print("🏆 FINAL RESULTS")
    print("=" * 85)
    print(f"{'Strategy':<12} | {'TPS':<8} | {'Client Avg':<12} | {'Server Avg':<12} | {'Server P99':<12}")
    print("-" * 85)
    
    for r in results:
        print(f"{r['strategy']:<12} | {r['tps']:<8.2f} | {r['avg_latency']:<12.2f} | {r['avg_server']:<12.2f} | {r['p99_server']:<12.2f}")
    
    print("\n💡 Client Avg = HTTP 왕복 시간 (네트워크 포함)")
    print("💡 Server Avg = 순수 서버 처리 시간 (API 내부)")
    print("💡 트리거: trigger 전략만 ON, 나머지는 OFF로 테스트됨")

