-- =================================================================
-- Git V1.0 - Logis-Flow 초기 스키마 (DDL)
-- =================================================================

-- 고객사 정보 테이블
CREATE TABLE companies (
    company_id INT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(100) NOT NULL
);

-- 창고 정보 테이블
CREATE TABLE warehouses (
    warehouse_id INT PRIMARY KEY AUTO_INCREMENT,
    warehouse_name VARCHAR(100) NOT NULL,
    address VARCHAR(255)
);

-- 상품 마스터 정보 테이블
CREATE TABLE products (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(100) NOT NULL
);

-- 화물 정보 테이블 (Shipment)
CREATE TABLE shipments (
    shipment_id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT,
    origin_warehouse_id INT,
    destination_warehouse_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    FOREIGN KEY (origin_warehouse_id) REFERENCES warehouses(warehouse_id),
    FOREIGN KEY (destination_warehouse_id) REFERENCES warehouses(warehouse_id)
);

-- 화물-상품 다대다 관계 테이블 (Shipment Items)
CREATE TABLE shipment_items (
    shipment_id INT,
    product_id INT,
    quantity INT NOT NULL,
    PRIMARY KEY (shipment_id, product_id), -- 복합 기본 키
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- 화물 상태 변경 로그 테이블 (Shipment Updates)
CREATE TABLE shipment_updates (
    update_id INT PRIMARY KEY AUTO_INCREMENT,
    shipment_id INT,
    status_code VARCHAR(50) NOT NULL,
    notes VARCHAR(255),
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
);

-- 성능 분석을 위한 필수 인덱스 추가 (배송 이력 조회 최적화)
CREATE INDEX idx_shipment_updates_shipment_id_timestamp
ON shipment_updates(shipment_id, timestamp);