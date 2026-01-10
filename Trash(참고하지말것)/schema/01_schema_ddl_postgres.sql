-- =================================================================
-- [PostgreSQL] Logis-Flow 초기 스키마 (DDL)
-- =================================================================

-- 0. 기존 테이블 정리를 위한 DROP (필요 시 주석 해제)
DROP TABLE IF EXISTS shipment_updates CASCADE;
DROP TABLE IF EXISTS shipment_items CASCADE;
DROP TABLE IF EXISTS shipments CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS warehouses CASCADE;
DROP TABLE IF EXISTS companies CASCADE;

-- 1. 고객사 정보 테이블
CREATE TABLE companies (
    company_id SERIAL PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL
);

-- 2. 창고 정보 테이블
CREATE TABLE warehouses (
    warehouse_id SERIAL PRIMARY KEY,
    warehouse_name VARCHAR(100) NOT NULL,
    address VARCHAR(255)
);

-- 3. 상품 마스터 정보 테이블
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL
);

-- 4. 화물 정보 테이블 (Shipment)
CREATE TABLE shipments (
    shipment_id SERIAL PRIMARY KEY,
    company_id INT,
    origin_warehouse_id INT,
    destination_warehouse_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    FOREIGN KEY (origin_warehouse_id) REFERENCES warehouses(warehouse_id),
    FOREIGN KEY (destination_warehouse_id) REFERENCES warehouses(warehouse_id)
);

-- 5. 화물-상품 다대다 관계 테이블 (Shipment Items)
CREATE TABLE shipment_items (
    shipment_id INT,
    product_id INT,
    quantity INT NOT NULL,
    PRIMARY KEY (shipment_id, product_id),
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- 6. 화물 상태 변경 로그 테이블 (Shipment Updates)
CREATE TABLE shipment_updates (
    update_id SERIAL PRIMARY KEY,
    shipment_id INT,
    status_code VARCHAR(50) NOT NULL,
    notes VARCHAR(255),
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
);

-- 성능 분석을 위한 인덱스
CREATE INDEX idx_shipment_updates_shipment_id_timestamp
ON shipment_updates(shipment_id, timestamp);
