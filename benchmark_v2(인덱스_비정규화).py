import pymysql
import psutil
import time
import threading

# ==========================================
# [설정] DB 접속 정보 (비밀번호 확인!)
# ==========================================
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'test1234',  # ★ 비밀번호 입력 ★
    'db': 'shipment',
    'charset': 'utf8mb4'
}

class ResourceMonitor:
    def __init__(self, target_name="mysqld"):
        self.monitoring = False
        self.cpu_logs = []
        self.mem_logs = []
        self.target_process = None
        
        candidates = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                if target_name.lower() in proc.info['name'].lower():
                    mem_usage = proc.info['memory_info'].rss
                    candidates.append((mem_usage, proc))
            except: continue
        
        if candidates:
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
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    
    print(f"\n🚀 [{query_name}] 실행...")
    monitor = ResourceMonitor(target_name="mysqld")
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
    # 1. 정규화 (인덱스 사용 O)
    # 아까의 '+ 0' 트릭을 제거하여 정상적으로 인덱스를 타게 합니다.
    normalized_index_sql = """
    SELECT SQL_NO_CACHE s.shipment_id, 
        (SELECT status_code FROM shipment_updates u 
         WHERE u.shipment_id = s.shipment_id  -- 인덱스 정상 사용
         ORDER BY timestamp DESC LIMIT 1) 
    FROM shipments s LIMIT 1000
    """

    # 2. 비정규화 (컬럼 직접 조회)
    denormalized_sql = """
    SELECT SQL_NO_CACHE s.shipment_id, s.current_status
    FROM shipments s LIMIT 1000
    """
    
    run_query("1. 정규화 + 인덱스 사용 (Normal)", normalized_index_sql)
    time.sleep(2)
    run_query("2. 비정규화 (Denormalized)", denormalized_sql)