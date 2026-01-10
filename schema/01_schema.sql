-- =============================================================================
-- LogisFlow 스마트 물류 플랫폼 - PostgreSQL 스키마 정의
-- =============================================================================
-- 
-- 📌 파일 실행 순서: Docker 컨테이너 초기화 시 알파벳 순으로 자동 실행
--    01_schema.sql → 02_indexes.sql → 03_seed_data.sql
--
-- 📌 비정규화 전략 (README Q2 답변):
--    shipments 테이블에 current_status, last_updated_at 등을 추가하여
--    500억 건의 shipment_updates 테이블을 매번 조회하지 않도록 최적화
--
-- 📌 동료 개발자 참고:
--    - Q3 (정합성): shipment_updates INSERT 시 shipments.current_status 동기화
--    - Q4 (조회최적화): shipment_updates 파티셔닝 또는 Elasticsearch 이관
--    - Q5 (ILM): 오래된 shipment_updates 파티션 아카이빙
-- =============================================================================

-- 기존 테이블 정리 (개발 환경용)
DROP TABLE IF EXISTS shipment_updates CASCADE;
DROP TABLE IF EXISTS shipment_items CASCADE;
DROP TABLE IF EXISTS shipments CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS warehouses CASCADE;
DROP TABLE IF EXISTS companies CASCADE;

-- =============================================================================
-- 1. 고객사 테이블 (Companies)
-- =============================================================================
-- 역할: B2B 고객사 (화주, 운송사) 정보 저장
-- 예상 규모: 약 1만 개
-- =============================================================================
CREATE TABLE companies (
    company_id SERIAL PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE companies IS '고객사 정보 (화주, 운송사)';
COMMENT ON COLUMN companies.company_id IS '고객사 고유 ID';
COMMENT ON COLUMN companies.company_name IS '고객사명';

-- =============================================================================
-- 2. 창고 테이블 (Warehouses)
-- =============================================================================
-- 역할: 물류 창고 정보 (출발지/도착지)
-- 예상 규모: 약 5만 개
-- =============================================================================
CREATE TABLE warehouses (
    warehouse_id SERIAL PRIMARY KEY,
    warehouse_name VARCHAR(100) NOT NULL,
    address VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE warehouses IS '창고 정보';
COMMENT ON COLUMN warehouses.warehouse_id IS '창고 고유 ID';
COMMENT ON COLUMN warehouses.warehouse_name IS '창고명';
COMMENT ON COLUMN warehouses.address IS '창고 주소';

-- =============================================================================
-- 3. 상품 테이블 (Products)
-- =============================================================================
-- 역할: 상품 마스터 정보
-- 예상 규모: 약 1천만 개
-- =============================================================================
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE products IS '상품 마스터 정보';
COMMENT ON COLUMN products.product_id IS '상품 고유 ID';
COMMENT ON COLUMN products.product_name IS '상품명';

-- =============================================================================
-- 4. 화물 테이블 (Shipments) ⭐ 비정규화 적용
-- =============================================================================
-- 역할: 화물 정보 + 비정규화된 현재 상태
-- 예상 규모: 약 5억 건 (목표: 천만 건 테스트)
--
-- ★ 비정규화 컬럼 (Q2 답변 구현):
--    - current_status: 현재 상태 (shipment_updates 조회 불필요)
--    - last_updated_at: 마지막 업데이트 시간
--    - origin_warehouse_name: 출발 창고명 (JOIN 제거)
--    - destination_warehouse_name: 도착 창고명 (JOIN 제거)
-- =============================================================================
CREATE TABLE shipments (
    shipment_id SERIAL PRIMARY KEY,
    
    -- 외래 키 관계
    company_id INT REFERENCES companies(company_id),
    origin_warehouse_id INT REFERENCES warehouses(warehouse_id),
    destination_warehouse_id INT REFERENCES warehouses(warehouse_id),
    
    -- 생성 시간
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- =========================================================================
    -- ⬇️ 비정규화 컬럼 (README Q2 답변 구현) ⬇️
    -- =========================================================================
    -- 현재 상태: shipment_updates의 최신 상태를 복제
    -- Q3에서 동기화 전략 테스트 (동기 트랜잭션 / 트리거 / Kafka)
    current_status VARCHAR(50) DEFAULT 'PENDING',
    
    -- 마지막 업데이트 시간
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 창고명 비정규화 (JOIN 제거용)
    origin_warehouse_name VARCHAR(100),
    destination_warehouse_name VARCHAR(100)
);

COMMENT ON TABLE shipments IS '화물 정보 (비정규화 적용)';
COMMENT ON COLUMN shipments.shipment_id IS '화물 고유 ID';
COMMENT ON COLUMN shipments.current_status IS '[비정규화] 현재 상태 - shipment_updates 최신값 복제';
COMMENT ON COLUMN shipments.last_updated_at IS '[비정규화] 마지막 상태 변경 시간';
COMMENT ON COLUMN shipments.origin_warehouse_name IS '[비정규화] 출발 창고명 - JOIN 제거용';
COMMENT ON COLUMN shipments.destination_warehouse_name IS '[비정규화] 도착 창고명 - JOIN 제거용';

-- =============================================================================
-- 5. 화물-상품 연결 테이블 (Shipment Items)
-- =============================================================================
-- 역할: 화물과 상품의 다대다 관계
-- 예상 규모: 약 50억 건
-- =============================================================================
CREATE TABLE shipment_items (
    shipment_id INT NOT NULL REFERENCES shipments(shipment_id) ON DELETE CASCADE,
    product_id INT NOT NULL REFERENCES products(product_id),
    quantity INT NOT NULL DEFAULT 1,
    
    PRIMARY KEY (shipment_id, product_id)
);

COMMENT ON TABLE shipment_items IS '화물-상품 연결 (다대다)';
COMMENT ON COLUMN shipment_items.quantity IS '상품 수량';

-- =============================================================================
-- 6. 상태 변경 로그 테이블 (Shipment Updates) ⭐ Q4 파티셔닝 대상
-- =============================================================================
-- 역할: 화물 상태 변경 이력 (Append-Only 로그)
-- 예상 규모: 약 500억 건 (목표: 1억 건 테스트)
--
-- ★ Q4 최적화:
--    - 방안 1: 이 테이블을 timestamp 기준 월별 파티셔닝
--    - 방안 2: Elasticsearch로 이관하여 분산 조회
--
-- ★ Q5 ILM:
--    - 오래된 파티션을 S3 Glacier로 아카이빙
-- =============================================================================
CREATE TABLE shipment_updates (
    update_id BIGSERIAL,  -- 대용량 대비 BIGSERIAL
    shipment_id INT NOT NULL,
    status_code VARCHAR(50) NOT NULL,
    notes VARCHAR(255),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 일반 테이블용 PK (파티셔닝 시 복합 PK로 변경 필요)
    PRIMARY KEY (update_id),
    
    -- 외래 키
    CONSTRAINT fk_shipment 
        FOREIGN KEY (shipment_id) 
        REFERENCES shipments(shipment_id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE shipment_updates IS '화물 상태 변경 로그 (Q4 파티셔닝 대상, Q5 ILM 대상)';
COMMENT ON COLUMN shipment_updates.update_id IS '로그 고유 ID (BIGSERIAL)';
COMMENT ON COLUMN shipment_updates.status_code IS '상태 코드 (PENDING, PICKED_UP, IN_TRANSIT, DELIVERED 등)';
COMMENT ON COLUMN shipment_updates.notes IS '상태 변경 메모';
COMMENT ON COLUMN shipment_updates.timestamp IS '상태 변경 시간 (파티셔닝 키)';

-- =============================================================================
-- 상태 코드 참조 (ENUM 대신 문자열 사용 - 유연성)
-- =============================================================================
-- PENDING      : 주문 접수
-- PICKED_UP    : 집화 완료
-- IN_TRANSIT   : 터미널 간 이동 중
-- OUT_DELIVERY : 배송 출발
-- DELIVERED    : 배송 완료
-- RETURNED     : 반품
-- =============================================================================

-- 스키마 생성 완료 로그
DO $$
BEGIN
    RAISE NOTICE '✅ LogisFlow 스키마 생성 완료!';
    RAISE NOTICE '   - companies, warehouses, products';
    RAISE NOTICE '   - shipments (비정규화 컬럼 포함)';
    RAISE NOTICE '   - shipment_items, shipment_updates';
END $$;
