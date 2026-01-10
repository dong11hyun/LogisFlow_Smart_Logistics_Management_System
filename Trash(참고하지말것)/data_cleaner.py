import pymysql

# ==========================================
# 1. DB 연결 설정 (이전과 동일하게 유지)
# ==========================================
db_config = {
    'host': 'localhost',
    'user': 'root',       
    'password': 'test1234',  # 본인 비밀번호 확인
    'db': 'shipment',        # DB 이름 확인
    'charset': 'utf8mb4'
}

def clean_generated_data(start_id):
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        print("🗑️ 추가된 데이터 삭제를 시작합니다...")
        
        # 외래 키 제약 조건 때문에 자식 테이블부터 삭제해야 합니다 (역순)
        
        # 1. Shipment_Updates (배송 이력 로그) 삭제
        # 3000건의 화물 ID와 관련된 모든 로그 삭제
        cursor.execute("DELETE FROM shipment_updates WHERE shipment_id >= %s", (start_id,))
        updates_deleted = cursor.rowcount
        
        # 2. Shipment_Items (화물 상품 연결) 삭제
        cursor.execute("DELETE FROM shipment_items WHERE shipment_id >= %s", (start_id,))
        items_deleted = cursor.rowcount
        
        # 3. Shipments (화물) 삭제
        # Python 스크립트로 삽입된 화물 레코드 삭제
        cursor.execute("DELETE FROM shipments WHERE shipment_id >= %s", (start_id,))
        shipments_deleted = cursor.rowcount
        
        # 4. Companies, Warehouses, Products (기초 데이터) 삭제
        # ID가 20(회사) 또는 53(상품) 이상인 레코드는 Python이 넣은 데이터로 간주하고 삭제
        # *주의: 이 부분은 ID가 연속적이지 않으면 일부 초기 데이터가 남아있을 수 있습니다.*
        
        cursor.execute("DELETE FROM companies WHERE company_id > 2")
        companies_deleted = cursor.rowcount
        
        cursor.execute("DELETE FROM warehouses WHERE warehouse_id > 30")
        warehouses_deleted = cursor.rowcount

        cursor.execute("DELETE FROM products WHERE product_id > 103")
        products_deleted = cursor.rowcount

        conn.commit()
        
        print("\n✅ 데이터 삭제 및 초기화 완료:")
        print(f"- 삭제된 화물 레코드 (Shipments): {shipments_deleted}건")
        print(f"- 삭제된 이력 로그 (Updates): {updates_deleted}건")
        print(f"- 삭제된 연결 데이터 (Items): {items_deleted}건")
        print(f"- 삭제된 기초 데이터 (Companies, Warehouses, Products): {companies_deleted + warehouses_deleted + products_deleted}건")
        
        print("\n💡 초기 SQL로 삽입한 시드 데이터만 남아있습니다.")

    except Exception as e:
        conn.rollback()
        print(f"❌ 오류 발생: {e}")
        print("💡 힌트: 삭제를 시도하기 전에 DB 서비스가 실행 중인지 확인해주세요.")
    finally:
        conn.close()

if __name__ == "__main__":
    # ----------------------------------------------------------------------
    # ★★ 중요: 삭제 기준 ID 설정 ★★
    # - 수동으로 넣은 마지막 화물 ID는 1002번이었습니다.
    # - 따라서 1003번부터 삭제하면 초기 시드 데이터는 안전하게 보존됩니다.
    # ----------------------------------------------------------------------
    CLEANUP_START_SHIPMENT_ID = 1003
    clean_generated_data(CLEANUP_START_SHIPMENT_ID)