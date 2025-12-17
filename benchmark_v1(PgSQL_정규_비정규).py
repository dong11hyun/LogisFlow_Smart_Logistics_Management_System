import psycopg2
import psutil
import time
import threading

# ==========================================
# [설정] PostgreSQL 접속 정보
# ==========================================
db_config = {
    'host': 'localhost',
    'user': 'postgres',      # 기본 계정 (필요 시 수정)
    'password': '',  # ★ 비밀번호 입력 ★
    'dbname': 'shipment',    # DB 이름
}

class ResourceMonitor:
    def __init__(self, target_name="postgres"):
        self.monitoring = False
        self.cpu_logs = []
        self.target_process = None
        
        candidates = []
        # PostgreSQL 프로세스 찾기 (메모리 사용량 기준)
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                if target_name.lower() in proc.info['name'].lower():
                    mem_usage = proc.info['memory_info'].rss
                    candidates.append((mem_usage, proc))
            except: continue
        
        if candidates:
            # 가장 메모리를 많이 쓰는 프로세스를 메인으로 간주
            candidates.sort(key=lambda x: x[0], reverse=True)
            self.target_process = candidates[0][1]

    def start(self):
        self.monitoring = True
        self.cpu_logs = []
        def monitor_loop():
            while self.monitoring:
                try:
                    if self.target_process:
                        self.cpu_logs.append(self.target_process.cpu_percent(interval=None))
                    else:
                        self.cpu_logs.append(psutil.cpu_percent(interval=None))
                    time.sleep(0.1)
                except: break
        self.thread = threading.Thread(target=monitor_loop)
        self.thread.start()

    def stop(self):
        self.monitoring = False
        self.thread.join()
        valid_cpu = [c for c in self.cpu_logs if c > 0]
        avg_cpu = sum(valid_cpu) / len(valid_cpu) if valid_cpu else 0
        return avg_cpu

def run_query(query_name, sql):
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    # (선택 사항) 확실한 비교를 위해 매번 캐시를 비우는 것과 유사한 효과를 주려면
    # DB 설정을 건드려야 하지만, 여기서는 SQL 트릭으로 풀스캔을 유도합니다.
    
    print(f"\n🚀 [{query_name}] 실행...")
    monitor = ResourceMonitor(target_name="postgres")
    monitor.start()
    
    start_time = time.time()
    try:
        cursor.execute(sql)
        cursor.fetchall()
    except Exception as e:
        print(f"⚠️ 쿼리 오류: {e}")
    
    end_time = time.time()
    avg_cpu = monitor.stop()
    duration = end_time - start_time
    
    print("-" * 50)
    print(f"⏱️  소요 시간 : {duration:.4f} 초")
    print(f"🔥  평균 CPU  : {avg_cpu:.1f} %")
    print("-" * 50)
    conn.close()

if __name__ == "__main__":
    # 1. 정규화 (강제 풀스캔 - SLOW)
    # WHERE 절의 (u.shipment_id::text || '') 부분 때문에 인덱스를 탈 수 없습니다.
    # ::text로 형변환을 하여 문자열 결합을 하면 옵티마이저는 인덱스를 포기하고 풀스캔합니다.
    full_scan_sql = """
    SELECT s.shipment_id, 
        (SELECT status_code FROM shipment_updates u 
         WHERE (u.shipment_id::text || '') = s.shipment_id::text
         ORDER BY timestamp DESC LIMIT 1) 
    FROM shipments s LIMIT 1000
    """

    # 2. 비정규화 (컬럼 직접 조회 - FAST)
    denormalized_sql = """
    SELECT s.shipment_id, s.current_status
    FROM shipments s LIMIT 1000
    """
    
    print("=== PostgreSQL 벤치마크 시작 ===")
    
    # 첫 번째 실행: 풀스캔 (느림)
    run_query("1. 정규화 + 풀스캔 강제 (Slow)", full_scan_sql)
    
    time.sleep(2) # 잠시 대기
    
    # 두 번째 실행: 비정규화 (빠름)
    run_query("2. 비정규화 (Fast)", denormalized_sql)