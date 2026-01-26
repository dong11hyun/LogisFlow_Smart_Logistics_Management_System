import pymysql
from faker import Faker
import random
from datetime import datetime, timedelta
from tqdm import tqdm

# ==========================================
# 1. DB 연결 설정
# ==========================================
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # ★ 본인의 비밀번호 입력 필수 ★
    'db': 'shipment',
    'charset': 'utf8mb4'
}

fake = Faker('ko_KR')

# ==========================================
# 2. 설정값
# ==========================================
TARGET_SHIPMENTS = 50000      
BATCH_SIZE = 5000             

def get_ids(cursor, table, col):
    cursor.execute(f"SELECT {col} FROM {table}")
    return [row[0] for row in cursor.fetchall()]

def generate_bulk_data():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        print(f"🚀 [Logis-Flow] 데이터 생성을 시작합니다. 목표 화물 수: {TARGET_SHIPMENTS}건")

        # 기초 데이터 보강
        print("📦 기초 데이터 보강 중...")
        companies = [(fake.company(),) for _ in range(50)]
        warehouses = [(f"{fake.city()} 센터 {i}", fake.address()) for i in range(50)]
        products = [(f"Logis 상품 {i}",) for i in range(100)]
        
        cursor.executemany("INSERT INTO companies (company_name) VALUES (%s)", companies)
        cursor.executemany("INSERT INTO warehouses (warehouse_name, address) VALUES (%s, %s)", warehouses)
        cursor.executemany("INSERT INTO products (product_name) VALUES (%s)", products)
        conn.commit()

        company_ids = get_ids(cursor, "companies", "company_id")
        warehouse_ids = get_ids(cursor, "warehouses", "warehouse_id")
        product_ids = get_ids(cursor, "products", "product_id")

        if not company_ids:
            print("❌ 기초 데이터가 없습니다.")
            return

        print("🚚 화물 및 로그 대량 생성 시작...")

        shipment_buffer = []
        item_buffer = []
        update_buffer = []

        for i in tqdm(range(TARGET_SHIPMENTS), desc="데이터 생성 중"):
            comp_id = random.choice(company_ids)
            origin, dest = random.sample(warehouse_ids, 2)
            created_at = fake.date_time_between(start_date='-2y', end_date='now')
            
            shipment_buffer.append((comp_id, origin, dest, created_at))

            # 배치 저장
            if len(shipment_buffer) >= BATCH_SIZE:
                cursor.executemany("""
                    INSERT INTO shipments (company_id, origin_warehouse_id, destination_warehouse_id, created_at)
                    VALUES (%s, %s, %s, %s)
                """, shipment_buffer)
                conn.commit()
                
                # 방금 저장된 ID 대역 조회
                cursor.execute(f"SELECT shipment_id, created_at FROM shipments ORDER BY shipment_id DESC LIMIT {BATCH_SIZE}")
                recent_shipments = cursor.fetchall()
                
                shipment_buffer = []

                for s_id, s_date in recent_shipments:
                    # [수정된 부분] 중복 없는 상품 뽑기 (random.sample 사용)
                    num_items = random.randint(1, 5)
                    # 전체 상품 목록에서 num_items 만큼 중복 없이 뽑음
                    selected_products = random.sample(product_ids, num_items)
                    
                    for pid in selected_products:
                        item_buffer.append((s_id, pid, random.randint(1, 100)))
                    
                    # Updates 생성
                    status_list = ['주문접수', '집화처리', '간선상차', '간선하차', '터미널입고', '터미널출고', '배송출발', '배송완료']
                    history_count = random.randint(3, 15)
                    current_time = s_date
                    
                    for _ in range(history_count):
                        status = random.choice(status_list)
                        current_time += timedelta(hours=random.randint(1, 48))
                        update_buffer.append((s_id, status, "시스템 자동 업데이트", current_time))

                cursor.executemany("INSERT INTO shipment_items (shipment_id, product_id, quantity) VALUES (%s, %s, %s)", item_buffer)
                cursor.executemany("INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES (%s, %s, %s, %s)", update_buffer)
                
                conn.commit()
                item_buffer = []
                update_buffer = []

        print("\n✅ 데이터 생성이 완료되었습니다!")

    except Exception as e:
        conn.rollback()
        print(f"❌ 오류 발생: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    generate_bulk_data()