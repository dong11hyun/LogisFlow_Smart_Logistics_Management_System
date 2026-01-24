# =============================================================================
# LogisFlow 천만 건 데이터 생성기 - 병렬 처리 (Multiprocessing) 버전
# =============================================================================
#
# 📌 개선 사항:
#   1. 멀티프로세싱 도입: CPU 코어를 최대한 활용하여 데이터 생성 속도 획기적 개선
#   2. COPY 방식 적용: INSERT 문 대신 TSV 파일 생성 후 Bulk Insert (속도 ↑)
#   3. 기존 로직 유지: Faker 사용, 비정규화 컬럼, 상태 흐름 등 비즈니스 로직 동일
#
# 📌 사용법:
#   python generate_10m.py
# =============================================================================

import psycopg2
from psycopg2 import extras
from faker import Faker
import random
from datetime import datetime, timedelta
import time
import sys
import os
import tempfile
from multiprocessing import Pool, cpu_count

# =============================================================================
# 1. 설정 (Configuration)
# =============================================================================

# 데이터베이스 연결 정보 (docker-compose 환경)
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'user': 'postgres',
    'password': 'logisflow1234',
    'dbname': 'logisflow'
}

# 데이터 생성 설정
TARGET_SHIPMENTS = 10_000_000        # 1,000만 건
CHUNK_SIZE = 100_000                 # 워커당 10만 건씩 처리 (메모리 관리 용이)
NUM_WORKERS = max(1, cpu_count() - 1)  # CPU 코어 - 1개 사용

SEED_VALUE = 999
DATE_START = datetime(2024, 1, 1)
DATE_END = datetime(2026, 11, 30)
PARTITION_MAX = datetime(2026, 12, 31, 23, 59, 59)

STATUS_FLOW = ['PENDING', 'PICKED_UP', 'IN_TRANSIT', 'OUT_DELIVERY', 'DELIVERED']

# =============================================================================
# 2. 유틸리티 함수
# =============================================================================

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def format_time(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}분 {secs}초"

# =============================================================================
# 3. 워커 함수 (병렬 처리)
# =============================================================================

def generate_chunk(args):
    """청크 단위 데이터 생성 (워커 프로세스에서 실행)"""
    chunk_id, start_id, end_id, temp_dir = args
    
    # 각 워커별 독립적인 시드 설정
    worker_seed = SEED_VALUE + chunk_id
    random.seed(worker_seed)
    Faker.seed(worker_seed)
    fake = Faker('ko_KR')
    
    # 임시 파일 경로
    shipments_file = os.path.join(temp_dir, f"shipments_{chunk_id}.tsv")
    items_file = os.path.join(temp_dir, f"items_{chunk_id}.tsv")
    updates_file = os.path.join(temp_dir, f"updates_{chunk_id}.tsv")
    
    # ID 범위 가정 (generate_master_data와 동일해야 함)
    company_ids_range = (1, 1000)
    warehouse_ids_range = (1, 1000)
    product_ids_range = (1, 10000)
    
    with open(shipments_file, 'w', encoding='utf-8') as sf, \
         open(items_file, 'w', encoding='utf-8') as itf, \
         open(updates_file, 'w', encoding='utf-8') as uf:
        
        current_shipment_id = start_id
        
        # 미리 도시 이름 리스트 생성 (Faker 호출 오버헤드 감소용 - 선택적 최적화)
        # 루프 내에서 fake.city()를 호출해도 되지만, 속도를 위해 일부 값을 변수로 관리 가능
        # 여기서는 원본 로직 유지를 위해 루프 내 호출 혹은 유사 동작 수행
        
        for _ in range(start_id, end_id + 1):
            # -----------------------------------------------------------------
            # (1) Shipment 생성
            # -----------------------------------------------------------------
            origin_id = random.randint(*warehouse_ids_range)
            dest_id = random.randint(*warehouse_ids_range)
            while dest_id == origin_id:
                dest_id = random.randint(*warehouse_ids_range)
            
            created_at = fake.date_time_between(start_date=DATE_START, end_date=DATE_END)
            
            # 원본 로직: fake.city() 사용
            origin_city = fake.city()
            dest_city = fake.city()
            origin_name = f"{origin_city} 물류센터 {origin_id - 1}"
            dest_name = f"{dest_city} 물류센터 {dest_id - 1}"
            
            final_status_idx = random.randint(0, len(STATUS_FLOW) - 1)
            current_status = STATUS_FLOW[final_status_idx]
            
            last_updated_at = min(
                created_at + timedelta(hours=random.randint(1, 72)),
                PARTITION_MAX
            )
            
            # TSV 쓰기 (Shipments)
            # 주의: COPY용 데이터는 탭(\t) 구분, None은 \N
            sf.write(f"{current_shipment_id}\t{random.randint(*company_ids_range)}\t"
                     f"{origin_id}\t{dest_id}\t{created_at}\t{current_status}\t"
                     f"{last_updated_at}\t{origin_name}\t{dest_name}\n")
            
            # -----------------------------------------------------------------
            # (2) Items 생성 (1~3개)
            # -----------------------------------------------------------------
            num_items = random.randint(1, 3)
            # random.sample은 population이 필요하므로 range 객체 사용
            selected_products = random.sample(range(product_ids_range[0], product_ids_range[1] + 1), num_items)
            
            for pid in selected_products:
                itf.write(f"{current_shipment_id}\t{pid}\t{random.randint(1, 100)}\n")
            
            # -----------------------------------------------------------------
            # (3) Updates 생성
            # -----------------------------------------------------------------
            num_logs = final_status_idx + 1
            log_time = created_at
            
            for step in range(num_logs):
                status = STATUS_FLOW[step]
                log_time += timedelta(hours=random.randint(1, 24))
                log_time = min(log_time, PARTITION_MAX)
                
                uf.write(f"{current_shipment_id}\t{status}\t{status} 처리 완료\t{log_time}\n")
            
            current_shipment_id += 1
            
    return chunk_id, end_id - start_id + 1

# =============================================================================
# 4. 데이터 초기화 및 마스터 데이터
# =============================================================================

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    
    print("\n🧹 [Phase 0] 테이블 초기화 (트랜잭션 데이터)...")
    cur.execute("TRUNCATE TABLE shipment_updates RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE TABLE shipment_items RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE TABLE shipments RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE TABLE products RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE TABLE warehouses RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE TABLE companies RESTART IDENTITY CASCADE;")
    
    # 대량 로딩을 위해 트리거/인덱스 잠시 비활성화 하면 좋지만, 
    # generate_100m_parallel.py 처럼 단순화하여 진행 (필요 시 추가)
    
    conn.commit()
    print("   ✅ 완료")
    conn.close()

def generate_master_data():
    conn = get_connection()
    cur = conn.cursor()
    fake = Faker('ko_KR')
    Faker.seed(SEED_VALUE)
    
    print("\n🏗️ [Phase 1] 마스터 데이터 생성 (Bulk Insert)...")
    
    # Companies
    temp_file = os.path.join(tempfile.gettempdir(), "companies.tsv")
    with open(temp_file, 'w', encoding='utf-8') as f:
        for i in range(1, 1001):
            f.write(f"{i}\t{fake.company()}\n")
    with open(temp_file, 'r', encoding='utf-8') as f:
        cur.copy_from(f, 'companies', columns=['company_id', 'company_name'])
    os.unlink(temp_file)
    print("   ✅ Companies 완료")
    
    # Warehouses
    temp_file = os.path.join(tempfile.gettempdir(), "warehouses.tsv")
    with open(temp_file, 'w', encoding='utf-8') as f:
        for i in range(1, 1001):
            city = fake.city()
            f.write(f"{i}\t{city} 물류센터 {i}\t{fake.address()}\n")
    with open(temp_file, 'r', encoding='utf-8') as f:
        cur.copy_from(f, 'warehouses', columns=['warehouse_id', 'warehouse_name', 'address'])
    os.unlink(temp_file)
    print("   ✅ Warehouses 완료")
    
    # Products
    temp_file = os.path.join(tempfile.gettempdir(), "products.tsv")
    with open(temp_file, 'w', encoding='utf-8') as f:
        prefixes = ["스마트폰", "노트북", "태블릿", "키보드", "마우스", "모니터", "이어폰", "충전기", "케이블", "케이스"]
        for i in range(1, 10001):
            name = f"{random.choice(prefixes)} {fake.word()} {i}"
            f.write(f"{i}\t{name}\n")
    with open(temp_file, 'r', encoding='utf-8') as f:
        cur.copy_from(f, 'products', columns=['product_id', 'product_name'])
    os.unlink(temp_file)
    print("   ✅ Products 완료")
    
    # 시퀀스 조정
    cur.execute("SELECT setval('companies_company_id_seq', 1000, true);")
    cur.execute("SELECT setval('warehouses_warehouse_id_seq', 1000, true);")
    cur.execute("SELECT setval('products_product_id_seq', 10000, true);")
    
    conn.commit()
    conn.close()

# =============================================================================
# 5. 메인 함수
# =============================================================================

def main():
    print("=" * 60)
    print("🚀 LogisFlow 데이터 생성기 v2.0 (Parallel & Bulk Load)")
    print("=" * 60)
    print(f"   목표: {TARGET_SHIPMENTS:,} 화물")
    print(f"   워커: {NUM_WORKERS}개 (CPU 코어 활용)")
    print("=" * 60)
    
    response = input("\n⚠️  기존 데이터가 삭제됩니다. 계속? (yes/no): ").strip().lower()
    if response != 'yes':
        print("❌ 취소됨")
        return
    
    start_time = time.time()
    
    # 1. 초기화 및 마스터 데이터
    init_db()
    generate_master_data()
    
    # 2. 청크 준비
    print(f"\n🔥 [Phase 2] 병렬 트랜잭션 데이터 생성...")
    temp_dir = tempfile.mkdtemp(prefix="logisflow_10m_")
    chunks = []
    for i in range(0, TARGET_SHIPMENTS, CHUNK_SIZE):
        start_id = i + 1
        end_id = min(i + CHUNK_SIZE, TARGET_SHIPMENTS)
        chunks.append((len(chunks), start_id, end_id, temp_dir))
    
    total_chunks = len(chunks)
    completed = 0
    
    # 3. 병렬 실행
    # Windows에서는 if __name__ == "__main__": 블록 필수 (multiprocessing)
    with Pool(NUM_WORKERS) as pool:
        for _ in pool.imap_unordered(generate_chunk, chunks):
            completed += 1
            progress = completed / total_chunks * 100
            elapsed = time.time() - start_time
            print(f"\r   ⏳ 생성: {progress:5.1f}% ({completed}/{total_chunks} 청크)", end="")
            
    print(f"\n   ✅ 파일 생성 완료")
    
    # 4. DB 적재 (COPY)
    print(f"\n📥 [Phase 3] DB로 Bulk Load (COPY)...")
    conn = get_connection()
    cur = conn.cursor()
    
    # 성능을 위해 트리거/제약조건 비활성화 추천되지만 안전하게 진행
    # (필요시 ALTER TABLE ... DISABLE TRIGGER ALL 추가)
    
    for i, (chunk_id, _, _, _) in enumerate(chunks):
        shipments_file = os.path.join(temp_dir, f"shipments_{chunk_id}.tsv")
        items_file = os.path.join(temp_dir, f"items_{chunk_id}.tsv")
        updates_file = os.path.join(temp_dir, f"updates_{chunk_id}.tsv")
        
        try:
            with open(shipments_file, 'r', encoding='utf-8') as f:
                cur.copy_from(f, 'shipments', columns=[
                    'shipment_id', 'company_id', 'origin_warehouse_id', 'destination_warehouse_id',
                    'created_at', 'current_status', 'last_updated_at',
                    'origin_warehouse_name', 'destination_warehouse_name'])
            
            with open(items_file, 'r', encoding='utf-8') as f:
                cur.copy_from(f, 'shipment_items', columns=['shipment_id', 'product_id', 'quantity'])
            
            with open(updates_file, 'r', encoding='utf-8') as f:
                cur.copy_from(f, 'shipment_updates', columns=['shipment_id', 'status_code', 'notes', 'timestamp'])
                
            conn.commit()
            
        except Exception as e:
            print(f"\n❌ Copy Fail (Chunk {chunk_id}): {e}")
            conn.rollback()
            break
        
        # 파일 정리
        try:
            os.unlink(shipments_file)
            os.unlink(items_file)
            os.unlink(updates_file)
        except:
            pass
            
        print(f"\r   ⏳ 적재: {(i+1)/total_chunks*100:5.1f}% ({i+1}/{total_chunks})", end="")

    # 5. 마무리
    print("\n\n⚙️ [Phase 4] 시퀀스 동기화...")
    cur.execute(f"SELECT setval('shipments_shipment_id_seq', {TARGET_SHIPMENTS}, true);")
    conn.commit()
    conn.close()
    
    try:
        os.rmdir(temp_dir)
    except:
        pass
    
    total_elapsed = time.time() - start_time
    print(f"\n✅ 전체 완료! (소요: {format_time(total_elapsed)})")
    
if __name__ == "__main__":
    main()
