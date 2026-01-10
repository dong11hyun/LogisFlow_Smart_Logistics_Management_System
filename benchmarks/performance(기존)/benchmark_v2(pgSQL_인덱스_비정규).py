import psycopg2  # PostgreSQL용 라이브러리
import psutil
import time
import threading

# ==========================================
# [설정] PostgreSQL 접속 정보
# ==========================================
db_config = {
    'host': 'localhost',
    'user': 'postgres',      # PostgreSQL 기본 유저는 보통 'postgres' 입니다.
    'password': '',  # ★ 비밀번호 확인 ★
    'dbname': 'shipment',    # MySQL의 'db' 키 대신 'dbname'을 사용합니다.
}

class ResourceMonitor:
    def __init__(self, target_name="postgres"):  # 타겟 프로세스 이름 변경
        self.monitoring = False
        self.cpu_logs = []
        self.mem_logs = []
        self.target_process = None
        
        candidates = []
        # PostgreSQL 프로세스 찾기
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                if target_name.lower() in proc.info['name'].lower():
                    mem_usage = proc.info['memory_info'].rss
                    candidates.append((mem_usage, proc))
            except: continue
        
        if candidates:
            # 메모리 사용량이 가장 높은 프로세스를 메인으로 간주
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
    # pymysql 대신 psycopg2 사용
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    print(f"\n🚀 [{query_name}] 실행...")
    monitor = ResourceMonitor(target_name="postgres")
    monitor.start()
    
    start_time = time.time()
    cursor.execute(sql)
    cursor.fetchall()
    end_time = time.time()
    
    avg_cpu = monitor.stop()
    duration = end_time - start_time
    
    print("-" * 50)
    print(f"⏱️  소요 시간 : {duration:.4f} 초")
    print(f"🔥  평균 CPU  : {avg_cpu:.1f} %")
    print("-" * 50)
    conn.close()

if __name__ == "__main__":
    # PostgreSQL에서는 SQL_NO_CACHE 힌트를 지원하지 않으므로 제거했습니다.
    # 정확한 벤치마킹을 위해서는 DB 서버 재시작 등이 필요할 수 있습니다.

    # 1. 정규화 (인덱스 사용 O)
    normalized_index_sql = """
    SELECT s.shipment_id, 
        (SELECT status_code FROM shipment_updates u 
         WHERE u.shipment_id = s.shipment_id  -- 인덱스 정상 사용
         ORDER BY timestamp DESC LIMIT 1) 
    FROM shipments s LIMIT 1000
    """

    # 2. 비정규화 (컬럼 직접 조회)
    denormalized_sql = """
    SELECT s.shipment_id, s.current_status
    FROM shipments s LIMIT 1000
    """
    
    run_query("1. 정규화 + 인덱스 사용 (Normal)", normalized_index_sql)
    time.sleep(2)
    run_query("2. 비정규화 (Denormalized)", denormalized_sql)