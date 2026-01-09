import psycopg2
from psycopg2 import extras
from faker import Faker
import random
from datetime import datetime, timedelta
import time

# ==========================================
# 1. 설정 (Configuration)
# ==========================================
db_config = {
    'host': 'localhost',
    'user': 'postgres',      # ★ 사용자명 확인 (기본값: postgres)
    'password': '',  # ★ 비밀번호 설정 필수 ★
    'dbname': 'shipment'     # ★ DB 생성 필수 (CREATE DATABASE shipment;)
}

# 목표 데이터 개수 설정 (1,000만 건)
TARGET_UPDATES = 10_000_000  
BATCH_SIZE = 5000            # execute_values 배치 사이즈
SEED_VALUE = 999             # 고정 시드

fake = Faker('ko_KR')
Faker.seed(SEED_VALUE)
random.seed(SEED_VALUE)

def get_connection():
    return psycopg2.connect(**db_config)

def truncate_tables():
    """기존 데이터를 모두 삭제하여 초기화 (MySQL과 다르게 CASCADE 사용)"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        print("🧹 [Clean Up] 기존 데이터 삭제(Truncate) 시작... (CASCADE)")
        
        # PostgreSQL은 CASCADE 하나로 의존성 있는 테이블까지 싹 지워짐
        # RESTART IDENTITY: 시퀀스 번호를 1로 초기화
        tables = ['shipment_updates', 'shipment_items', 'shipments', 'products', 'warehouses', 'companies']
        # 테이블 존재 여부 확인 후 Truncate 하는 것이 안전하지만, 여기선 Bulk Reset 가정
        cur.execute(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE;")
        
        conn.commit()
        print("   - 모든 테이블 초기화 완료")
        
    except Exception as e:
        print(f"❌ 초기화 중 오류: {e}")
        if conn: conn.rollback()
        raise
    finally:
        if conn: conn.close()

def generate_master_data():
    """기초 데이터(회사, 창고, 상품) 생성"""
    conn = get_connection()
    cur = conn.cursor()
    print("\n🏗️ [Phase 1] 기초 데이터(Master Data) 생성 중...")

    try:
        # 1. Companies (1,000개)
        companies = [(fake.company(),) for _ in range(1000)]
        extras.execute_values(cur, "INSERT INTO companies (company_name) VALUES %s", companies)
        print(f"   - Companies: 1,000건 생성 완료")

        # 2. Warehouses (1,000개)
        warehouses = [(f"{fake.city()} 물류센터 {i}", fake.address()) for i in range(1000)]
        extras.execute_values(cur, "INSERT INTO warehouses (warehouse_name, address) VALUES %s", warehouses)
        print(f"   - Warehouses: 1,000건 생성 완료")

        # 3. Products (10,000개)
        product_names =["마우스", "키보드", "모니터", "책상", "의자", "노트북", "태블릿", "스마트폰", "충전기", "이어폰"]
        products = [(f"{random.choice(product_names)} {fake.word()} {i}",) for i in range(10000)]
        extras.execute_values(cur, "INSERT INTO products (product_name) VALUES %s", products)
        print(f"   - Products: 10,000건 생성 완료")

        conn.commit()
        
        # ID 캐싱 
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
    print(f"\n🚀 [Phase 2] 트랜잭션 데이터 생성 시작 (PostgreSQL)...")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # 목표 달성을 위한 계산 (보수적 적용: 3)
    AVG_UPDATES_PER_SHIPMENT = 3
    TOTAL_SHIPMENTS = TARGET_UPDATES // AVG_UPDATES_PER_SHIPMENT
    
    print(f"   - 목표 화물 수: {TOTAL_SHIPMENTS:,} 건")
    print(f"   - 예상 로그 수: {TARGET_UPDATES:,} 건")
    
    status_flow = ['주문접수', '집화완료', '터미널간이동', '배송중', '배송완료']
    
    shipments_buffer = []
    items_buffer = []
    updates_buffer = []

    start_time = time.time()
    total_updates = 0
    current_shipment_id = 1 
    
    try:
        for i in range(TOTAL_SHIPMENTS):
            # (1) Shipment 생성 (ID 명시적 삽입을 위해 포함하지 않음 - RESTART IDENTITY 믿음)
            # PG SERIAL은 1부터 시작 보장 (Truncate 했으므로)
            origin = random.choice(w_ids)
            dest = random.choice(w_ids)
            created_at = fake.date_time_between(start_date='-1y', end_date='now')
            
            # 명시적으로 ID를 넣어서 Python 카운터와 DB ID 싱크를 100% 맞춤
            shipments_buffer.append((
                current_shipment_id, random.choice(c_ids), origin, dest, created_at
            ))

            # (2) Items 생성
            num_items = random.randint(1, 3)
            selected_products = random.sample(p_ids, num_items)
            for pid in selected_products:
                items_buffer.append((
                    current_shipment_id, pid, random.randint(1, 100)
                ))

            # (3) Updates 생성
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

            # (4) Batch Insert (psycopg2 execute_values 사용)
            if len(shipments_buffer) >= BATCH_SIZE:
                # Shipments (ID 명시 삽입)
                extras.execute_values(
                    cur, 
                    "INSERT INTO shipments (shipment_id, company_id, origin_warehouse_id, destination_warehouse_id, created_at) VALUES %s", 
                    shipments_buffer
                )
                # Items
                extras.execute_values(
                    cur, 
                    "INSERT INTO shipment_items (shipment_id, product_id, quantity) VALUES %s", 
                    items_buffer
                )
                # Updates
                extras.execute_values(
                    cur, 
                    "INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES %s", 
                    updates_buffer
                )
                conn.commit()
                
                # 진행률 출력
                elapsed = time.time() - start_time
                if elapsed > 0:
                    rate = total_updates / elapsed
                    print(f"\r   ⏳ 진행률: {total_updates:,} / {TARGET_UPDATES:,} rows ({rate:.0f} rows/sec)", end="")
                
                shipments_buffer = []
                items_buffer = []
                updates_buffer = []

        # 남은 데이터 처리
        if shipments_buffer:
            extras.execute_values(cur, "INSERT INTO shipments (shipment_id, company_id, origin_warehouse_id, destination_warehouse_id, created_at) VALUES %s", shipments_buffer)
            extras.execute_values(cur, "INSERT INTO shipment_items (shipment_id, product_id, quantity) VALUES %s", items_buffer)
            extras.execute_values(cur, "INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES %s", updates_buffer)
            conn.commit()

        # 시퀀스 동기화 (ID를 명시적으로 넣었으므로, 시퀀스를 마지막 ID로 업데이트해줘야 함)
        print(f"\n⚙️ [Post-Process] 시퀀스 번호 동기화 중...")
        cur.execute(f"SELECT setval('shipments_shipment_id_seq', {current_shipment_id}, false)")
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
    print(f"🔥 [PostgreSQL 10 Million Generator] 시작합니다 (Seed: {SEED_VALUE})")
    print("⚠️  주의: 반드시 'shipment' DB가 존재해야 합니다. (schema 파일 참조)")
    print("5초 뒤 시작...")
    time.sleep(5)
    
    truncate_tables()
    c_ids, w_ids, p_ids = generate_master_data()
    generate_transaction_data(c_ids, w_ids, p_ids)
