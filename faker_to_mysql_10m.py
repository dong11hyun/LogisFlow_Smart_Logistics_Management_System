import pymysql
from faker import Faker
import random
from datetime import datetime, timedelta
import time

# ==========================================
# 1. 설정 (Configuration)
# ==========================================
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'test1234',  # ★ 본인의 비밀번호 입력 필수 ★
    'db': 'shipment',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# 목표 데이터 개수 설정
TARGET_UPDATES = 10_000_000  # 1,000만 건 (Shipment Updates 기준)
BATCH_SIZE = 5000            # 한 번에 INSERT할 행 수 (튜닝 가능)
SEED_VALUE = 999             # ★ 동료와 동일한 데이터를 만들기 위한 고정 시드 ★

# Faker 및 Random 시드 고정
fake = Faker('ko_KR')
Faker.seed(SEED_VALUE)
random.seed(SEED_VALUE)

def get_connection():
    return pymysql.connect(**db_config)

def truncate_tables():
    """기존 데이터를 모두 삭제하여 초기화 (FK 의존성 역순)"""
    conn = get_connection()
    cursor = conn.cursor()
    print("🧹 [Clean Up] 기존 데이터 삭제(Truncate) 시작... (FK 체크 해제)")
    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        tables = ['shipment_updates', 'shipment_items', 'shipments', 'products', 'warehouses', 'companies']
        for table in tables:
            cursor.execute(f"TRUNCATE TABLE {table};")
            print(f"   - {table} 초기화 완료")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
    except Exception as e:
        print(f"❌ 초기화 중 오류: {e}")
        conn.rollback()
    finally:
        conn.close()

def generate_master_data():
    """기초 데이터(회사, 창고, 상품) 생성"""
    conn = get_connection()
    cursor = conn.cursor()
    print("\n🏗️ [Phase 1] 기초 데이터(Master Data) 생성 중...")

    try:
        # 1. Companies (1,000개)
        companies = [(fake.company(),) for _ in range(1000)]
        cursor.executemany("INSERT INTO companies (company_name) VALUES (%s)", companies)
        print(f"   - Companies: 1,000건 생성 완료")

        # 2. Warehouses (1,000개)
        warehouses = [(f"{fake.city()} 물류센터 {i}", fake.address()) for i in range(1000)]
        cursor.executemany("INSERT INTO warehouses (warehouse_name, address) VALUES (%s, %s)", warehouses)
        print(f"   - Warehouses: 1,000건 생성 완료")

        # 3. Products (10,000개)
        product_names = ["마우스", "키보드", "모니터", "책상", "의자", "노트북", "태블릿", "스마트폰", "충전기", "이어폰"]
        products = [(f"{random.choice(product_names)} {fake.word()} {i}",) for i in range(10000)]
        cursor.executemany("INSERT INTO products (product_name) VALUES (%s)", products)
        print(f"   - Products: 10,000건 생성 완료")

        conn.commit()
        
        # ID 캐싱 (Insert 성능 향상용)
        # AUTO_INCREMENT가 1부터 시작한다고 가정하고 범위로 생성
        company_ids = list(range(1, 1001))
        warehouse_ids = list(range(1, 1001))
        product_ids = list(range(1, 10001))
        
        return company_ids, warehouse_ids, product_ids

    except Exception as e:
        print(f"❌ 기초 데이터 생성 오류: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def generate_transaction_data(c_ids, w_ids, p_ids):
    """트랜잭션 데이터(화물, 아이템, 로그) 대량 생성"""
    print(f"\n🚀 [Phase 2] 트랜잭션 데이터 {TARGET_UPDATES//10000}만 건 생성 시작...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 목표 달성을 위한 계산
    # 화물 1개당 평균 3개의 Update 로그가 생긴다고 가정 (보수적으로 잡아서 화물 수를 늘림)
    AVG_UPDATES_PER_SHIPMENT = 3 
    TOTAL_SHIPMENTS = TARGET_UPDATES // AVG_UPDATES_PER_SHIPMENT
    
    print(f"   - 목표 화물 수: {TOTAL_SHIPMENTS:,} 건 (확실한 1,000만 달성을 위해 상향 조정)")
    print(f"   - 예상 로그 수: {TARGET_UPDATES:,} 건")
    print(f"   - 배치 사이즈: {BATCH_SIZE}")

    status_flow = ['주문접수', '집화완료', '터미널간이동', '배송중', '배송완료']
    
    shipments_buffer = []
    items_buffer = []
    updates_buffer = []

    start_time = time.time()
    total_updates = 0

    try:
        # Shipment ID는 1부터 순차 증가한다고 가정 (Bulk Insert 최적화)
        current_shipment_id = 1 
        
        for i in range(TOTAL_SHIPMENTS):
            # (1) Shipment 생성
            origin = random.choice(w_ids)
            dest = random.choice(w_ids)
            created_at = fake.date_time_between(start_date='-1y', end_date='now')
            
            shipments_buffer.append((
                random.choice(c_ids), origin, dest, created_at
            ))

            # (2) Items 생성 (화물당 1~3개 상품)
            num_items = random.randint(1, 3)
            selected_products = random.sample(p_ids, num_items)
            for pid in selected_products:
                items_buffer.append((
                    current_shipment_id, pid, random.randint(1, 100)
                ))

            # (3) Updates 생성 (화물당 1~5단계 로그)
            num_logs = random.randint(1, 5)
            log_time = created_at
            for step in range(num_logs):
                status = status_flow[step]
                log_time += timedelta(hours=random.randint(1, 12))
                updates_buffer.append((
                    current_shipment_id, 
                    status, 
                    f"System Auto Note {step}", 
                    log_time
                ))
            
            current_shipment_id += 1
            total_updates += num_logs

            # (4) Batch Insert
            if len(shipments_buffer) >= BATCH_SIZE:
                cursor.executemany(
                    "INSERT INTO shipments (company_id, origin_warehouse_id, destination_warehouse_id, created_at) VALUES (%s, %s, %s, %s)",
                    shipments_buffer
                )
                cursor.executemany(
                    "INSERT INTO shipment_items (shipment_id, product_id, quantity) VALUES (%s, %s, %s)",
                    items_buffer
                )
                cursor.executemany(
                    "INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES (%s, %s, %s, %s)",
                    updates_buffer
                )
                conn.commit()
                
                # 진행률 출력
                elapsed = time.time() - start_time
                if elapsed > 0:
                    rate = total_updates / elapsed
                    print(f"\r   ⏳ 진행률: {total_updates:,} / {TARGET_UPDATES:,} rows ({rate:.0f} rows/sec)", end="")
                
                # 버퍼 비우기
                shipments_buffer = []
                items_buffer = []
                updates_buffer = []

        # 남은 데이터 처리
        if shipments_buffer:
            cursor.executemany("INSERT INTO shipments (company_id, origin_warehouse_id, destination_warehouse_id, created_at) VALUES (%s, %s, %s, %s)", shipments_buffer)
            cursor.executemany("INSERT INTO shipment_items (shipment_id, product_id, quantity) VALUES (%s, %s, %s)", items_buffer)
            cursor.executemany("INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES (%s, %s, %s, %s)", updates_buffer)
            conn.commit()

        total_elapsed = time.time() - start_time
        print(f"\n\n✅ 완료! 총 {total_updates:,} 건의 로그 데이터 생성.")
        print(f"⏱️ 소요 시간: {total_elapsed/60:.2f} 분")
        
    except Exception as e:
        print(f"\n❌ 트랜잭션 데이터 생성 중 오류: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print(f"🔥 [10 Million Generator] 시작합니다 (Seed: {SEED_VALUE})")
    print("⚠️  주의: 기존 데이터를 모두 삭제합니다. 5초 뒤 시작...")
    time.sleep(5)
    
    truncate_tables()
    c_ids, w_ids, p_ids = generate_master_data()
    generate_transaction_data(c_ids, w_ids, p_ids)
