import pymysql
import time
import threading
import queue
import random
from datetime import datetime

# ==========================================
# 1. 환경 설정 (DB 접속 정보)
# ==========================================
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # ★ 본인의 비밀번호 입력 필수 ★
    'db': 'shipment',
    'charset': 'utf8mb4',
    'autocommit': True
}

# 테스트할 횟수 (각 전략당)
TEST_ITERATIONS = 100 

class ConsistencyBenchmark:
    def __init__(self):
        self.conn = pymysql.connect(**db_config)
        self.cursor = self.conn.cursor()
        self.shipment_ids = self._fetch_shipment_ids()
        
        # 비동기 처리를 위한 큐와 워커 스레드 설정
        self.msg_queue = queue.Queue()
        self.worker_running = True
        self.worker_thread = threading.Thread(target=self._async_worker)
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def _fetch_shipment_ids(self, limit=100):
        """테스트에 사용할 존재하는 화물 ID 목록 가져오기"""
        self.cursor.execute(f"SELECT shipment_id FROM shipments LIMIT {limit}")
        return [row[0] for row in self.cursor.fetchall()]

    def _get_random_target(self):
        """랜덤한 화물 ID와 새로운 상태값 생성"""
        s_id = random.choice(self.shipment_ids)
        new_status = random.choice(['집화완료', '터미널입고', '배송출발', '배송완료', '수취확인'])
        return s_id, new_status

    # ---------------------------------------------------------
    # 전략 1: 동기적 애플리케이션 트랜잭션 (Sync Transaction)
    # ---------------------------------------------------------
    def strategy_sync_transaction(self):
        s_id, status = self._get_random_target()
        start_time = time.time()
        
        try:
            self.conn.begin()
            
            # 1. 로그 적재
            self.cursor.execute(
                "INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES (%s, %s, %s, NOW())",
                (s_id, status, "Sync Update")
            )
            
            # 2. 상태 동기화 + 🔥[부하 주입] 0.05초 강제 지연 (DB Lock 시뮬레이션)
            # 실제로는 복잡한 연산이나 Lock 대기 시간이 발생한다고 가정
            self.cursor.execute(
                """
                UPDATE shipments 
                SET current_status = %s, last_updated_at = NOW() 
                WHERE shipment_id = %s 
                AND SLEEP(0.05) = 0 
                """,
                (status, s_id)
            )
            
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error: {e}")

        latency = time.time() - start_time
        return latency, s_id, status

    # ---------------------------------------------------------
    # 전략 2: 데이터베이스 트리거 (DB Trigger)
    # ---------------------------------------------------------
    def setup_trigger(self):
        # 🔥[부하 주입] 트리거 내부에 DO SLEEP(0.05) 추가
        trigger_sql = """
        CREATE TRIGGER after_shipment_update 
        AFTER INSERT ON shipment_updates 
        FOR EACH ROW 
        BEGIN
            UPDATE shipments 
            SET current_status = NEW.status_code, last_updated_at = NEW.timestamp
            WHERE shipment_id = NEW.shipment_id;
            
            -- 트리거가 실행될 때 DB가 바빠서 0.05초 걸린다고 가정
            DO SLEEP(0.05);
        END;
        """
        try:
            self.cursor.execute("DROP TRIGGER IF EXISTS after_shipment_update")
            self.cursor.execute(trigger_sql)
            print("✅ [Setup] DB 트리거 (with Latency) 생성 완료")
        except Exception as e:
            print(f"Trigger Error: {e}")

    # (teardown_trigger와 strategy_db_trigger는 기존과 동일하지만, 
    #  DB 내부에서 SLEEP이 돌기 때문에 strategy_db_trigger 실행 시 자동으로 느려집니다.)

    def teardown_trigger(self):
        """트리거 삭제 (테스트 후 정리)"""
        self.cursor.execute("DROP TRIGGER IF EXISTS after_shipment_update")
        print("🧹 [Cleanup] DB 트리거 삭제 완료")

    def strategy_db_trigger(self):
        s_id, status = self._get_random_target()
        start_time = time.time()
        
        # 앱에서는 INSERT만 수행 (UPDATE는 트리거가 함)
        self.cursor.execute(
            "INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES (%s, %s, %s, NOW())",
            (s_id, status, "Trigger Update")
        )
        # 커밋은 autocommit=True라 생략 혹은 명시
        
        latency = time.time() - start_time
        return latency, s_id, status

    # ---------------------------------------------------------
    # 전략 3: 비동기 메시지 큐 (Async Queue)
    # ---------------------------------------------------------
    def _async_worker(self):
        worker_conn = pymysql.connect(**db_config)
        worker_cursor = worker_conn.cursor()
        
        while self.worker_running:
            try:
                task = self.msg_queue.get(timeout=1)
                if task:
                    s_id, status = task
                    
                    # 🔥[부하 주입] 워커 스레드는 느리게 처리함 (사용자와 무관)
                    worker_cursor.execute(
                        """
                        UPDATE shipments 
                        SET current_status = %s, last_updated_at = NOW() 
                        WHERE shipment_id = %s 
                        AND SLEEP(0.05) = 0
                        """,
                        (status, s_id)
                    )
                    worker_conn.commit()
                    self.msg_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker Error: {e}")

    def strategy_async_queue(self):
        s_id, status = self._get_random_target()
        start_time = time.time()
        
        # 1. 로그 적재
        self.cursor.execute(
            "INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES (%s, %s, %s, NOW())",
            (s_id, status, "Async Update")
        )
        
        # 2. 큐에 던지기 (Fire & Forget)
        self.msg_queue.put((s_id, status))
        
        # 사용자는 여기서 해방됨 (매우 빠름)
        latency = time.time() - start_time
        return latency, s_id, status

    # ---------------------------------------------------------
    # 공통: 정합성 검증 (Verification)
    # ---------------------------------------------------------
    def check_consistency(self, s_id, expected_status):
        """DB를 조회해서 현재 상태가 기대값과 일치하는지 확인"""
        self.cursor.execute(f"SELECT current_status FROM shipments WHERE shipment_id = {s_id}")
        actual_status = self.cursor.fetchone()[0]
        return actual_status == expected_status

    # ---------------------------------------------------------
    # 벤치마크 실행기
    # ---------------------------------------------------------
    def run_benchmark(self, strategy_name, strategy_func, setup_func=None, teardown_func=None):
        print(f"\n🚀 [Test: {strategy_name}] 시작 ({TEST_ITERATIONS}회 반복)...")
        
        if setup_func: setup_func()
        
        latencies = []
        consistency_fails = 0
        
        # 워밍업
        strategy_func()
        
        for _ in range(TEST_ITERATIONS):
            # 전략 실행
            latency, s_id, expected = strategy_func()
            latencies.append(latency)
            
            # 즉시 일관성 확인 (Write 직후 Read)
            # 비동기 방식은 여기서 실패(False)가 떠야 정상입니다.
            if not self.check_consistency(s_id, expected):
                consistency_fails += 1
                
        if teardown_func: teardown_func()
        
        avg_latency = sum(latencies) / len(latencies)
        print(f"📊 결과 리포트 ({strategy_name})")
        print(f"   - 평균 소요 시간 (Latency): {avg_latency:.5f} 초")
        print(f"   - 쓰기 직후 데이터 불일치 횟수: {consistency_fails} / {TEST_ITERATIONS} 건")
        
        if consistency_fails > 0:
            print("   👉 해석: '최종 일관성(Eventual Consistency)' 모델이므로 직후 조회 시 불일치는 정상입니다.")
        else:
            print("   👉 해석: '강한 일관성(Strong Consistency)'이 보장됩니다.")

    def close(self):
        self.worker_running = False
        self.conn.close()

# ==========================================
# 실행부 (Main)
# ==========================================
if __name__ == "__main__":
    benchmark = ConsistencyBenchmark()
    
    try:
        # 1. 동기 트랜잭션 테스트
        benchmark.run_benchmark(
            "Strategy A: 동기 트랜잭션", 
            benchmark.strategy_sync_transaction
        )
        
        # 2. DB 트리거 테스트
        benchmark.run_benchmark(
            "Strategy B: DB 트리거", 
            benchmark.strategy_db_trigger,
            setup_func=benchmark.setup_trigger,
            teardown_func=benchmark.teardown_trigger
        )
        
        # 3. 비동기 큐 테스트
        benchmark.run_benchmark(
            "Strategy C: 비동기 큐 (Async)", 
            benchmark.strategy_async_queue
        )

        # 비동기 작업이 다 끝날 때까지 잠시 대기 (큐 비우기)
        print("\n⏳ 비동기 잔여 작업 처리 대기 중...")
        benchmark.msg_queue.join()
        print("✅ 모든 테스트 완료.")
        
    finally:
        benchmark.close()