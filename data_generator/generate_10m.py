# =============================================================================
# LogisFlow 천만 건 데이터 생성기 - 개선 버전
# =============================================================================
#
# 📌 주요 개선 사항:
#   1. DB 설정: 새 환경(logisflow, 포트 5433)에 맞춤
#   2. 날짜 범위: 파티션 테이블(2024~2026년)에 맞게 조정
#   3. 비정규화 컬럼: current_status, last_updated_at 등 동기화
#   4. 상태 코드: 영문 코드로 통일 (PENDING, DELIVERED 등)
#   5. 진행률 표시: 더 상세한 ETA 표시
#   6. 안전 장치: 기존 데이터 삭제 전 확인 절차
#
# 📌 사용법:
#   python generate_10m.py
#
# 📌 협업:
#   SEED_VALUE = 999로 고정되어 있어 동료도 동일한 데이터 생성 가능
# =============================================================================

import psycopg2
from psycopg2 import extras
from faker import Faker
import random
from datetime import datetime, timedelta
import time
import sys

# =============================================================================
# 1. 설정 (Configuration)
# =============================================================================

# 데이터베이스 연결 정보 (docker-compose 환경에 맞춤)
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,                    # ★ 변경: 5432 → 5433 (로컬 PostgreSQL과 충돌 방지)
    'user': 'postgres',
    'password': 'logisflow1234',     # ★ 변경: docker-compose.yml과 동일
    'dbname': 'logisflow'            # ★ 변경: shipment → logisflow
}

# 데이터 생성 설정
TARGET_SHIPMENTS = 10_000_000        # ★ 10배 증가: 1000만 건 화물 (async vs trigger 비교용)
AVG_UPDATES_PER_SHIPMENT = 3         # ★ 화물당 평균 3회 (전체 3000만 로그)
TARGET_UPDATES = TARGET_SHIPMENTS * AVG_UPDATES_PER_SHIPMENT  # 약 3000만 건 로그

BATCH_SIZE = 5000                    # 배치 크기
SEED_VALUE = 999                     # ★ 협업용 고정 시드

# 날짜 범위 (파티션 테이블에 맞춤)
DATE_START = datetime(2024, 1, 1)    # 파티션 시작일
DATE_END = datetime(2026, 11, 30)    # ★ 수정: 12월 말 → 11월 말 (시간 더해도 12월 내 유지)
PARTITION_MAX = datetime(2026, 12, 31, 23, 59, 59)  # 파티션 최대값

# 상태 코드 (영문 통일)
STATUS_FLOW = ['PENDING', 'PICKED_UP', 'IN_TRANSIT', 'OUT_DELIVERY', 'DELIVERED']

# 랜덤 시드 고정
random.seed(SEED_VALUE)
Faker.seed(SEED_VALUE)
fake = Faker('ko_KR')

# =============================================================================
# 2. 유틸리티 함수
# =============================================================================

def get_connection():
    """데이터베이스 연결"""
    return psycopg2.connect(**DB_CONFIG)

def format_time(seconds):
    """초를 분:초 형식으로 변환"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}분 {secs}초"

def confirm_truncate():
    """데이터 삭제 전 확인"""
    print("\n" + "=" * 60)
    print("⚠️  경고: 기존 데이터가 모두 삭제됩니다!")
    print("=" * 60)
    print(f"   - 대상 DB: {DB_CONFIG['dbname']}")
    print(f"   - 생성할 화물: {TARGET_SHIPMENTS:,} 건")
    print(f"   - 예상 상태 로그: {TARGET_UPDATES:,} 건")
    print(f"   - 시드 값: {SEED_VALUE}")
    print("=" * 60)
    
    response = input("\n계속 진행하시겠습니까? (yes/no): ").strip().lower()
    if response != 'yes':
        print("❌ 작업이 취소되었습니다.")
        sys.exit(0)

# =============================================================================
# 3. 데이터 초기화
# =============================================================================

def truncate_tables():
    """기존 데이터 삭제 (마스터 데이터 제외)"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        print("\n🧹 [Phase 0] 기존 트랜잭션 데이터 삭제 중...")
        
        # 트랜잭션 데이터만 삭제 (마스터 데이터는 유지 가능하도록 분리)
        cur.execute("TRUNCATE TABLE shipment_updates RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE shipment_items RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE shipments RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE products RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE warehouses RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE companies RESTART IDENTITY CASCADE;")
        
        conn.commit()
        print("   ✅ 테이블 초기화 완료")
        
    except Exception as e:
        print(f"   ❌ 초기화 오류: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

# =============================================================================
# 4. 마스터 데이터 생성
# =============================================================================

def generate_master_data():
    """기초 데이터 생성 (회사, 창고, 상품)"""
    conn = get_connection()
    cur = conn.cursor()
    
    print("\n🏗️ [Phase 1] 마스터 데이터 생성 중...")
    
    try:
        # Companies (1,000개)
        companies = [(fake.company(),) for _ in range(1000)]
        extras.execute_values(cur, "INSERT INTO companies (company_name) VALUES %s", companies)
        print(f"   ✅ Companies: 1,000건")
        
        # Warehouses (1,000개)
        warehouses = [(f"{fake.city()} 물류센터 {i}", fake.address()) for i in range(1000)]
        extras.execute_values(cur, "INSERT INTO warehouses (warehouse_name, address) VALUES %s", warehouses)
        print(f"   ✅ Warehouses: 1,000건")
        
        # Products (10,000개)
        product_prefixes = ["스마트폰", "노트북", "태블릿", "키보드", "마우스", "모니터", "이어폰", "충전기", "케이블", "케이스"]
        products = [(f"{random.choice(product_prefixes)} {fake.word()} {i}",) for i in range(10000)]
        extras.execute_values(cur, "INSERT INTO products (product_name) VALUES %s", products)
        print(f"   ✅ Products: 10,000건")
        
        conn.commit()
        
        # ID 범위 저장
        company_ids = list(range(1, 1001))
        warehouse_ids = list(range(1, 1001))
        product_ids = list(range(1, 10001))
        
        return company_ids, warehouse_ids, product_ids
        
    except Exception as e:
        print(f"   ❌ 마스터 데이터 생성 오류: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

# =============================================================================
# 5. 트랜잭션 데이터 생성 (핵심)
# =============================================================================

def generate_transaction_data(company_ids, warehouse_ids, product_ids):
    """화물, 아이템, 상태 로그 대량 생성"""
    
    print(f"\n🚀 [Phase 2] 트랜잭션 데이터 생성 시작...")
    print(f"   - 목표 화물: {TARGET_SHIPMENTS:,} 건")
    print(f"   - 예상 로그: {TARGET_UPDATES:,} 건")
    print(f"   - 날짜 범위: {DATE_START.date()} ~ {DATE_END.date()}")
    print("")
    
    conn = get_connection()
    cur = conn.cursor()
    
    shipments_buffer = []
    items_buffer = []
    updates_buffer = []
    
    start_time = time.time()
    total_updates = 0
    current_shipment_id = 1
    
    try:
        for i in range(TARGET_SHIPMENTS):
            # =====================================================
            # (1) Shipment 생성
            # =====================================================
            origin_id = random.choice(warehouse_ids)
            dest_id = random.choice(warehouse_ids)
            while dest_id == origin_id:  # 출발지 ≠ 도착지
                dest_id = random.choice(warehouse_ids)
            
            # 날짜: 파티션 범위 내에서 랜덤
            created_at = fake.date_time_between(start_date=DATE_START, end_date=DATE_END)
            
            # 창고명 조회 (비정규화용)
            origin_name = f"{fake.city()} 물류센터 {origin_id - 1}"
            dest_name = f"{fake.city()} 물류센터 {dest_id - 1}"
            
            # 최종 상태 결정 (랜덤)
            final_status_idx = random.randint(0, len(STATUS_FLOW) - 1)
            current_status = STATUS_FLOW[final_status_idx]
            
            # last_updated_at 계산 (파티션 범위 초과 방지)
            last_updated_at = min(
                created_at + timedelta(hours=random.randint(1, 72)),
                PARTITION_MAX
            )
            
            # Shipment 데이터 (비정규화 컬럼 포함)
            shipments_buffer.append((
                current_shipment_id,
                random.choice(company_ids),
                origin_id,
                dest_id,
                created_at,
                current_status,           # ★ 비정규화: current_status
                last_updated_at,          # ★ last_updated_at (범위 제한됨)
                origin_name,              # ★ origin_warehouse_name
                dest_name                 # ★ destination_warehouse_name
            ))
            
            # =====================================================
            # (2) Items 생성 (1~3개)
            # =====================================================
            num_items = random.randint(1, 3)
            selected_products = random.sample(product_ids, num_items)
            for pid in selected_products:
                items_buffer.append((
                    current_shipment_id, 
                    pid, 
                    random.randint(1, 100)
                ))
            
            # =====================================================
            # (3) Updates 생성 (상태 변경 이력)
            # =====================================================
            num_logs = final_status_idx + 1  # 최종 상태까지의 이력
            log_time = created_at
            
            for step in range(num_logs):
                status = STATUS_FLOW[step]
                log_time += timedelta(hours=random.randint(1, 24))
                # 파티션 범위 초과 방지
                log_time = min(log_time, PARTITION_MAX)
                updates_buffer.append((
                    current_shipment_id,
                    status,
                    f"{status} 처리 완료",
                    log_time
                ))
            
            current_shipment_id += 1
            total_updates += num_logs
            
            # =====================================================
            # (4) 배치 저장
            # =====================================================
            if len(shipments_buffer) >= BATCH_SIZE:
                # Shipments (비정규화 컬럼 포함)
                extras.execute_values(
                    cur,
                    """INSERT INTO shipments 
                       (shipment_id, company_id, origin_warehouse_id, destination_warehouse_id, 
                        created_at, current_status, last_updated_at, 
                        origin_warehouse_name, destination_warehouse_name) 
                       VALUES %s""",
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
                progress = (i + 1) / TARGET_SHIPMENTS * 100
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (TARGET_SHIPMENTS - i - 1) / rate if rate > 0 else 0
                
                print(f"\r   ⏳ 진행: {progress:5.1f}% | 화물: {i+1:,} | 로그: {total_updates:,} | "
                      f"속도: {rate:.0f}/초 | ETA: {format_time(eta)}", end="")
                
                # 버퍼 초기화
                shipments_buffer = []
                items_buffer = []
                updates_buffer = []
        
        # 남은 데이터 처리
        if shipments_buffer:
            extras.execute_values(
                cur,
                """INSERT INTO shipments 
                   (shipment_id, company_id, origin_warehouse_id, destination_warehouse_id,
                    created_at, current_status, last_updated_at,
                    origin_warehouse_name, destination_warehouse_name) 
                   VALUES %s""",
                shipments_buffer
            )
            extras.execute_values(cur, "INSERT INTO shipment_items (shipment_id, product_id, quantity) VALUES %s", items_buffer)
            extras.execute_values(cur, "INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES %s", updates_buffer)
            conn.commit()
        
        # 시퀀스 동기화
        print(f"\n\n⚙️ [Post] 시퀀스 동기화 중...")
        cur.execute(f"SELECT setval('shipments_shipment_id_seq', {current_shipment_id}, false)")
        conn.commit()
        
        total_elapsed = time.time() - start_time
        print(f"\n✅ 완료!")
        print(f"   - 생성된 화물: {TARGET_SHIPMENTS:,} 건")
        print(f"   - 생성된 로그: {total_updates:,} 건")
        print(f"   - 소요 시간: {format_time(total_elapsed)}")
        
    except Exception as e:
        print(f"\n❌ 트랜잭션 데이터 생성 오류: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

# =============================================================================
# 6. 메인 실행
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🔥 LogisFlow 데이터 생성기 v2.0")
    print("=" * 60)
    print(f"   시드: {SEED_VALUE} (협업용 고정)")
    print(f"   DB: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    
    confirm_truncate()
    
    print("\n⏳ 3초 후 시작...")
    time.sleep(3)
    
    truncate_tables()
    company_ids, warehouse_ids, product_ids = generate_master_data()
    generate_transaction_data(company_ids, warehouse_ids, product_ids)
    
    print("\n" + "=" * 60)
    print("🎉 데이터 생성 완료!")
    print("=" * 60)
