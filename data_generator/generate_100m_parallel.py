# =============================================================================
# LogisFlow 초고속 데이터 생성기 v4.0 (멀티프로세싱)
# =============================================================================
#
# 📌 최적화:
#   1. 멀티프로세싱 (CPU 코어 활용)
#   2. 청크 단위 병렬 생성
#   3. 임시 파일로 COPY (메모리 효율)
#
# 📌 예상 성능:
#   - 단일 코어: ~10,000건/초
#   - 멀티 코어: ~40,000건/초 (4배 향상)
# =============================================================================

import psycopg2
import random
from datetime import datetime, timedelta
import time
import sys
import os
import tempfile
from multiprocessing import Pool, cpu_count

# =============================================================================
# 설정
# =============================================================================

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'user': 'postgres',
    'password': 'logisflow1234',
    'dbname': 'logisflow'
}

TARGET_SHIPMENTS = 100_000_000       # 1억 건
NUM_WORKERS = max(1, cpu_count() - 1)  # CPU 코어 - 1개 사용
CHUNK_SIZE = 1_000_000               # 워커당 100만 건씩 처리

DATE_START = datetime(2024, 1, 1)
DATE_END = datetime(2026, 11, 30)
PARTITION_MAX = datetime(2026, 12, 31, 23, 59, 59)
STATUS_FLOW = ['PENDING', 'PICKED_UP', 'IN_TRANSIT', 'OUT_DELIVERY', 'DELIVERED']
CITIES = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '수원', '용인']

# =============================================================================
# 워커 함수 (멀티프로세싱)
# =============================================================================

def generate_chunk(args):
    """청크 단위 데이터 생성 (워커 프로세스에서 실행)"""
    chunk_id, start_id, end_id, temp_dir = args
    
    random.seed(999 + chunk_id)  # 청크별 다른 시드
    
    shipments_file = os.path.join(temp_dir, f"shipments_{chunk_id}.tsv")
    items_file = os.path.join(temp_dir, f"items_{chunk_id}.tsv")
    updates_file = os.path.join(temp_dir, f"updates_{chunk_id}.tsv")
    
    date_delta = (DATE_END - DATE_START).days
    
    with open(shipments_file, 'w', encoding='utf-8') as sf, \
         open(items_file, 'w', encoding='utf-8') as itf, \
         open(updates_file, 'w', encoding='utf-8') as uf:
        
        for shipment_id in range(start_id, end_id + 1):
            # Shipment
            origin_id = random.randint(1, 1000)
            dest_id = random.randint(1, 999) if origin_id == 1000 else random.randint(1, 1000)
            if dest_id == origin_id:
                dest_id = (dest_id % 1000) + 1
            
            random_days = random.randint(0, date_delta)
            created_at = DATE_START + timedelta(days=random_days, hours=random.randint(0, 23))
            final_status_idx = random.randint(0, 4)
            current_status = STATUS_FLOW[final_status_idx]
            last_updated_at = min(created_at + timedelta(hours=random.randint(1, 72)), PARTITION_MAX)
            
            origin_city = random.choice(CITIES)
            dest_city = random.choice(CITIES)
            
            sf.write(f"{shipment_id}\t{random.randint(1, 1000)}\t{origin_id}\t{dest_id}\t"
                    f"{created_at}\t{current_status}\t{last_updated_at}\t"
                    f"{origin_city} 물류센터\t{dest_city} 물류센터\n")
            
            # Items (1~2개)
            num_items = random.randint(1, 2)
            products = random.sample(range(1, 10001), num_items)
            for pid in products:
                itf.write(f"{shipment_id}\t{pid}\t{random.randint(1, 100)}\n")
            
            # Updates (최종 상태만)
            log_time = min(created_at + timedelta(hours=random.randint(1, 48)), PARTITION_MAX)
            uf.write(f"{shipment_id}\t{current_status}\t{current_status} 처리\t{log_time}\n")
    
    return chunk_id, end_id - start_id + 1

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}시간 {minutes}분"
    return f"{minutes}분 {secs}초"

# =============================================================================
# 메인 함수
# =============================================================================

def main():
    print("=" * 60)
    print("🚀 LogisFlow 초고속 데이터 생성기 v4.0 (멀티프로세싱)")
    print("=" * 60)
    print(f"   목표: {TARGET_SHIPMENTS:,} 화물")
    print(f"   워커: {NUM_WORKERS}개 (CPU 코어 활용)")
    print(f"   청크: {CHUNK_SIZE:,}건/청크")
    print("=" * 60)
    
    response = input("\n⚠️  기존 데이터가 삭제됩니다. 계속? (yes/no): ").strip().lower()
    if response != 'yes':
        print("❌ 취소됨")
        return
    
    start_time = time.time()
    
    # 1. DB 초기화
    print("\n🧹 [Phase 0] 테이블 초기화...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE shipment_updates RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE TABLE shipment_items RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE TABLE shipments RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE TABLE products RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE TABLE warehouses RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE TABLE companies RESTART IDENTITY CASCADE;")
    cur.execute("ALTER TABLE shipment_updates DISABLE TRIGGER ALL;")
    cur.execute("ALTER TABLE shipments DISABLE TRIGGER ALL;")
    conn.commit()
    print("   ✅ 완료")
    
    # 2. 마스터 데이터
    print("\n🏗️  [Phase 1] 마스터 데이터...")
    
    # Companies
    temp_file = os.path.join(tempfile.gettempdir(), "companies.tsv")
    with open(temp_file, 'w', encoding='utf-8') as f:
        for i in range(1, 1001):
            f.write(f"{i}\t회사_{i}\n")
    with open(temp_file, 'r', encoding='utf-8') as f:
        cur.copy_from(f, 'companies', columns=['company_id', 'company_name'])
    os.unlink(temp_file)
    
    # Warehouses
    temp_file = os.path.join(tempfile.gettempdir(), "warehouses.tsv")
    with open(temp_file, 'w', encoding='utf-8') as f:
        for i in range(1, 1001):
            city = random.choice(CITIES)
            f.write(f"{i}\t{city} 물류센터 {i}\t{city} 산업단지 {i}번길\n")
    with open(temp_file, 'r', encoding='utf-8') as f:
        cur.copy_from(f, 'warehouses', columns=['warehouse_id', 'warehouse_name', 'address'])
    os.unlink(temp_file)
    
    # Products
    temp_file = os.path.join(tempfile.gettempdir(), "products.tsv")
    with open(temp_file, 'w', encoding='utf-8') as f:
        products = ["스마트폰", "노트북", "태블릿", "키보드", "마우스"]
        for i in range(1, 10001):
            f.write(f"{i}\t{random.choice(products)}_{i}\n")
    with open(temp_file, 'r', encoding='utf-8') as f:
        cur.copy_from(f, 'products', columns=['product_id', 'product_name'])
    os.unlink(temp_file)
    
    cur.execute("SELECT setval('companies_company_id_seq', 1000, true);")
    cur.execute("SELECT setval('warehouses_warehouse_id_seq', 1000, true);")
    cur.execute("SELECT setval('products_product_id_seq', 10000, true);")
    conn.commit()
    print("   ✅ 완료")
    
    # 3. 청크 분할
    print(f"\n🔥 [Phase 2] 병렬 데이터 생성 (워커 {NUM_WORKERS}개)...")
    
    temp_dir = tempfile.mkdtemp(prefix="logisflow_")
    chunks = []
    for i in range(0, TARGET_SHIPMENTS, CHUNK_SIZE):
        start_id = i + 1
        end_id = min(i + CHUNK_SIZE, TARGET_SHIPMENTS)
        chunks.append((len(chunks), start_id, end_id, temp_dir))
    
    total_chunks = len(chunks)
    completed = 0
    
    # 4. 병렬 생성
    with Pool(NUM_WORKERS) as pool:
        for chunk_id, count in pool.imap_unordered(generate_chunk, chunks):
            completed += 1
            elapsed = time.time() - start_time
            progress = completed / total_chunks * 100
            eta = (elapsed / completed) * (total_chunks - completed) if completed > 0 else 0
            print(f"\r   ⏳ 생성: {progress:5.1f}% ({completed}/{total_chunks} 청크) | ETA: {format_time(eta)}", end="")
    
    print(f"\n   ✅ 파일 생성 완료")
    
    # 5. DB로 COPY
    print(f"\n📥 [Phase 3] DB로 COPY 중...")
    
    for i, (chunk_id, start_id, end_id, _) in enumerate(chunks):
        shipments_file = os.path.join(temp_dir, f"shipments_{chunk_id}.tsv")
        items_file = os.path.join(temp_dir, f"items_{chunk_id}.tsv")
        updates_file = os.path.join(temp_dir, f"updates_{chunk_id}.tsv")
        
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
        
        # 파일 삭제
        os.unlink(shipments_file)
        os.unlink(items_file)
        os.unlink(updates_file)
        
        progress = (i + 1) / total_chunks * 100
        print(f"\r   ⏳ COPY: {progress:5.1f}% ({i+1}/{total_chunks} 청크)", end="")
    
    os.rmdir(temp_dir)
    
    # 6. 마무리
    cur.execute(f"SELECT setval('shipments_shipment_id_seq', {TARGET_SHIPMENTS}, true);")
    cur.execute("ALTER TABLE shipment_updates ENABLE TRIGGER ALL;")
    cur.execute("ALTER TABLE shipments ENABLE TRIGGER ALL;")
    conn.commit()
    conn.close()
    
    total_elapsed = time.time() - start_time
    rate = TARGET_SHIPMENTS / total_elapsed
    
    print(f"\n\n✅ 완료!")
    print(f"   - 화물: {TARGET_SHIPMENTS:,} 건")
    print(f"   - 소요: {format_time(total_elapsed)}")
    print(f"   - 속도: {rate:,.0f} 건/초")
    print("\n" + "=" * 60)
    print("🎉 데이터 생성 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()
