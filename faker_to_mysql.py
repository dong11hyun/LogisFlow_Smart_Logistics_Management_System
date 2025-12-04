import pymysql
from faker import Faker
import random
from datetime import datetime, timedelta

# ==========================================
# 1. DB 연결 설정 (요청하신 정보 반영 완료)
# ==========================================
db_config = {
    'host': 'localhost',
    'user': 'root',       
    'password': 'test1234',  # 요청하신 비밀번호
    'db': 'shipment',        # 요청하신 DB 이름
    'charset': 'utf8mb4'
}

fake = Faker('ko_KR') # 한국어 데이터 생성

def get_existing_ids(cursor, table_name, id_column):
    """
    DB에서 현재 존재하는 ID 목록을 가져옵니다.
    외래 키 오류(Error 1452)를 방지하는 핵심 함수입니다.
    """
    cursor.execute(f"SELECT {id_column} FROM {table_name}")
    # 조회된 결과((1,), (2,), ...)를 리스트 [1, 2, ...]로 변환
    ids = [row[0] for row in cursor.fetchall()]
    return ids

def generate_data():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        print("🚀 데이터 생성을 시작합니다...")

        # --------------------------------------
        # 1. 기초 데이터 추가 생성 (규모 확장을 위해)
        # --------------------------------------
        # SQL로 이미 넣으신 데이터 외에 데이터를 좀 더 풍부하게 만듭니다.
        
        print("1. 회사, 창고, 상품 데이터 추가 생성 중...")
        
        # 회사 20개 추가
        companies_data = [(fake.company(),) for _ in range(20)]
        cursor.executemany("INSERT INTO companies (company_name) VALUES (%s)", companies_data)
        
        # 창고 20개 추가
        warehouses_data = [(f"{fake.city()} 물류센터", fake.address()) for _ in range(20)]
        cursor.executemany("INSERT INTO warehouses (warehouse_name, address) VALUES (%s, %s)", warehouses_data)

        # 상품 50개 추가
        product_names = [
            "게이밍 마우스", "무선 이어폰", "스마트워치", "태블릿 거치대", "보조배터리",
            "USB 허브", "기계식 키보드", "모니터 암", "웹캠", "블루투스 스피커"
        ]
        products_data = [(f"{random.choice(product_names)} {fake.word()}",) for _ in range(50)]
        cursor.executemany("INSERT INTO products (product_name) VALUES (%s)", products_data)
        
        conn.commit() # 기초 데이터 저장

        # --------------------------------------
        # 2. 존재하는 ID 조회 (★★핵심★★)
        # --------------------------------------
        # SQL로 직접 넣으신 ID(10, 20, 30)와 방금 파이썬으로 넣은 ID를 모두 가져옵니다.
        print("2. 외래 키 정합성을 위해 현재 ID 목록 조회 중...")
        
        company_ids = get_existing_ids(cursor, "companies", "company_id")
        warehouse_ids = get_existing_ids(cursor, "warehouses", "warehouse_id")
        product_ids = get_existing_ids(cursor, "products", "product_id")

        if not warehouse_ids or not company_ids:
            print("❌ 오류: 기초 데이터가 없습니다. SQL 코드를 먼저 실행해주세요.")
            return

        # --------------------------------------
        # 3. 화물(Shipments) 및 로그 대량 생성
        # --------------------------------------
        print("3. 화물 및 배송 이력 생성 시작 (대량 데이터)...")
        
        TOTAL_SHIPMENTS = 3000  # 생성할 화물 개수
        BATCH_SIZE = 100        # 한 번에 DB에 넣을 개수 (속도 최적화)
        
        STATUS_FLOW = ['주문접수', '집화완료', '터미널간이동', '배송중', '배송완료']

        # 배치 저장을 위한 리스트
        update_data_list = []
        item_data_list = []

        for i in range(TOTAL_SHIPMENTS):
            # (1) 화물 1건 생성 및 즉시 INSERT (ID 확보를 위해)
            comp_id = random.choice(company_ids)
            origin_id = random.choice(warehouse_ids)
            dest_id = random.choice(warehouse_ids)
            
            while origin_id == dest_id: # 출발지와 도착지가 같으면 다시 뽑기
                dest_id = random.choice(warehouse_ids)
            
            created_at = fake.date_time_between(start_date='-1y', end_date='now')

            # 화물 넣기
            cursor.execute("""
                INSERT INTO shipments (company_id, origin_warehouse_id, destination_warehouse_id, created_at)
                VALUES (%s, %s, %s, %s)
            """, (comp_id, origin_id, dest_id, created_at))
            
            # 방금 생성된 화물의 ID 가져오기 (AUTO_INCREMENT)
            current_shipment_id = cursor.lastrowid

            # (2) 화물-상품 연결 (Items) 데이터 준비
            num_items = random.randint(1, 3)
            selected_prods = random.sample(product_ids, num_items)
            for pid in selected_prods:
                qty = random.randint(1, 10)
                item_data_list.append((current_shipment_id, pid, qty))

            # (3) 배송 이력 (Updates) 데이터 준비
            num_updates = random.randint(1, 5) # 진행 단계 랜덤
            current_time = created_at
            
            for step in range(num_updates):
                status = STATUS_FLOW[step]
                current_time += timedelta(hours=random.randint(2, 24))
                note = f"{status} 처리 (담당자: {fake.last_name()}{fake.first_name()})"
                update_data_list.append((current_shipment_id, status, note, current_time))

            # (4) 일정량 쌓이면 DB에 저장 (Batch Insert)
            if len(item_data_list) >= BATCH_SIZE:
                cursor.executemany("INSERT INTO shipment_items (shipment_id, product_id, quantity) VALUES (%s, %s, %s)", item_data_list)
                cursor.executemany("INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES (%s, %s, %s, %s)", update_data_list)
                conn.commit()
                
                # 리스트 초기화
                item_data_list = []
                update_data_list = []
                print(f"  -> {i + 1} / {TOTAL_SHIPMENTS} 화물 처리 완료")

        # 남은 데이터 저장
        if item_data_list:
            cursor.executemany("INSERT INTO shipment_items (shipment_id, product_id, quantity) VALUES (%s, %s, %s)", item_data_list)
            cursor.executemany("INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES (%s, %s, %s, %s)", update_data_list)
            conn.commit()

        print("\n✅ 모든 데이터 생성이 성공적으로 완료되었습니다!")

    except Exception as e:
        conn.rollback()
        print(f"❌ 오류 발생: {e}")
        print("💡 힌트: DB 비밀번호나 DB 이름('shipment')이 맞는지 다시 확인해주세요.")
    finally:
        conn.close()

if __name__ == "__main__":
    generate_data()