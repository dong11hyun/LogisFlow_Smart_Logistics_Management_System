import pymysql
import psutil
import time
import threading

# ==========================================
# [설정] DB 접속 정보 (비밀번호 꼭 확인!)
# ==========================================
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'test1234',  # ★ 여기에 비밀번호 입력 ★
    'db': 'shipment',
    'charset': 'utf8mb4'
}

class ResourceMonitor:
    def __init__(self, target_name="mysqld"):
        self.monitoring = False
        self.cpu_logs = []
        self.mem_logs = []
        self.target_process = None
        
        # 1. 진짜 프로세스 찾기 (메모리를 가장 많이 쓰는 놈이 진짜다)
        candidates = []
        print(f"🔎 프로세스 탐색 중: '{target_name}'...")
        
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                # 대소문자 구분 없이 찾기
                if target_name.lower() in proc.info['name'].lower():
                    mem_usage = proc.info['memory_info'].rss
                    candidates.append((mem_usage, proc))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if candidates:
            # 메모리 사용량 순으로 정렬 (가장 큰 게 0번)
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_match = candidates[0]
            self.target_process = best_match[1]
            print(f"✅ 타겟 확정: PID={self.target_process.pid}, MEM={best_match[0]/1024/1024:.1f}MB (진짜 MySQL)")
        else:
            print(f"⚠️ 경고: '{target_name}' 프로세스를 찾을 수 없습니다. (시스템 전체 CPU 측정 모드로 전환)")

    def start(self):
        self.monitoring = True
        self.cpu_logs = []
        self.mem_logs = []
        
        def monitor_loop():
            # 첫 호출은 기준점이 되므로 0이 나올 수 있어 미리 한 번 호출
            if self.target_process:
                try:
                    self.target_process.cpu_percent(interval=None)
                except: pass

            while self.monitoring:
                try:
                    if self.target_process:
                        # 프로세스 전용
                        cpu = self.target_process.cpu_percent(interval=None)
                        mem = self.target_process.memory_info().rss / (1024 * 1024)
                    else:
                        # 시스템 전체 (Fallback)
                        cpu = psutil.cpu_percent(interval=None)
                        mem = 0
                    
                    self.cpu_logs.append(cpu)
                    self.mem_logs.append(mem)
                    time.sleep(0.5) # 부하를 줄이기 위해 0.5초 간격으로 변경
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break # 프로세스가 죽었거나 권한 없으면 중단
                    
        self.thread = threading.Thread(target=monitor_loop)
        self.thread.start()

    def stop(self):
        self.monitoring = False
        self.thread.join()
        
        # 평균 계산 (0.0% 제외하여 좀 더 정확하게)
        valid_cpu = [c for c in self.cpu_logs if c > 0]
        avg_cpu = sum(valid_cpu) / len(valid_cpu) if valid_cpu else 0
        max_cpu = max(self.cpu_logs) if self.cpu_logs else 0
        avg_mem = sum(self.mem_logs) / len(self.mem_logs) if self.mem_logs else 0
        
        return avg_cpu, max_cpu, avg_mem

def run_query(query_name, sql):
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    
    print(f"\n🚀 [{query_name}] 실행 준비...")
    monitor = ResourceMonitor(target_name="mysqld")
    monitor.start()
    
    print("   -> 쿼리 실행 중 (잠시만 기다려주세요)...")
    start_time = time.time()
    
    cursor.execute(sql)
    cursor.fetchall() # 데이터 다 가져오기
    
    end_time = time.time()
    avg_cpu, max_cpu, avg_mem = monitor.stop()
    duration = end_time - start_time
    
    print("-" * 50)
    print(f"⏱️  소요 시간 : {duration:.4f} 초")
    print(f"🔥  평균 CPU  : {avg_cpu:.1f} %")
    print(f"💥  최대 CPU  : {max_cpu:.1f} %")
    print(f"💾  평균 메모리: {avg_mem:.1f} MB")
    print("-" * 50)
    
    conn.close()

if __name__ == "__main__":
    # 1. 느린 쿼리 (인덱스 회피)
    slow_sql = """
    SELECT SQL_NO_CACHE s.shipment_id, 
        (SELECT status_code FROM shipment_updates u 
         WHERE (u.shipment_id + 0) = s.shipment_id 
         ORDER BY timestamp DESC LIMIT 1) 
    FROM shipments s LIMIT 1000
    """

    # 2. 빠른 쿼리 (비정규화)
    fast_sql = """
    SELECT SQL_NO_CACHE s.shipment_id, s.current_status
    FROM shipments s LIMIT 1000
    """
    
    # 쿼리 1 실행
    run_query("Before: 정규화 (Slow)", slow_sql)
    
    # 쿼리 2 실행
    time.sleep(3) # 열 식히기
    run_query("After: 비정규화 (Fast)", fast_sql)