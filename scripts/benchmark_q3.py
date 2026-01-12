import requests
import time
import statistics
import concurrent.futures
import random

# 설정
API_URL = "http://localhost:8000"
TOTAL_REQUESTS = 100  # 전략당 요청 횟수
CONCURRENCY = 10      # 동시 요청 수

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
        latency = (time.time() - start_time) * 1000  # ms
        return latency, True
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0, False

def run_benchmark(strategy):
    """특정 전략 벤치마크 실행"""
    print(f"\n🚀 Benchmarking Strategy: {strategy} ...")
    
    latencies = []
    success_count = 0
    
    # 1~1000번 화물에 대해 테스트
    shipment_ids = [random.randint(1, 1000000) for _ in range(TOTAL_REQUESTS)]
    
    start_total = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(send_request, sid, strategy) for sid in shipment_ids]
        
        for future in concurrent.futures.as_completed(futures):
            latency, success = future.result()
            if success:
                latencies.append(latency)
                success_count += 1
                
    total_time = time.time() - start_total
    tps = success_count / total_time
    
    print(f"✅ Completed {success_count}/{TOTAL_REQUESTS} requests in {total_time:.2f}s")
    print(f"📊 TPS: {tps:.2f}")
    print(f"⏱️ Avg Latency: {statistics.mean(latencies):.2f} ms")
    if latencies:
        print(f"⏱️ P99 Latency: {statistics.quantiles(latencies, n=100)[98]:.2f} ms")
    
    return {
        "strategy": strategy,
        "tps": tps,
        "avg_latency": statistics.mean(latencies) if latencies else 0,
        "p99_latency": statistics.quantiles(latencies, n=100)[98] if latencies else 0
    }

if __name__ == "__main__":
    print(f"🔥 Starting Q3 Benchmark (Requests: {TOTAL_REQUESTS}, Concurrency: {CONCURRENCY})")
    
    results = []
    
    # 전략 1: Sync
    results.append(run_benchmark("sync"))
    
    # 전략 2: Trigger (DB 트리거가 활성화되어 있어야 함)
    results.append(run_benchmark("trigger"))
    
    # 전략 3: Async (Kafka)
    results.append(run_benchmark("async"))
    
    print("\n=========================================")
    print("🏆 FINAL RESULTS")
    print("=========================================")
    print(f"{'Strategy':<10} | {'TPS':<10} | {'Avg (ms)':<10} | {'P99 (ms)':<10}")
    print("-" * 50)
    
    for r in results:
        print(f"{r['strategy']:<10} | {r['tps']:<10.2f} | {r['avg_latency']:<10.2f} | {r['p99_latency']:<10.2f}")
