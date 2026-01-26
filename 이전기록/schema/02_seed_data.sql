-- =================================================================
-- Git V1.1 - 초기 시드 데이터 (DML)
-- 이 데이터는 Python Faker 스크립트가 실행되기 전의 기준선 역할을 합니다.
-- =================================================================
SET NAMES utf8mb4;

-- 1. 고객사 데이터
INSERT INTO companies (company_id, company_name) VALUES
(1, 'FastLogi'),
(2, 'QuickCommerce');

-- 2. 창고 데이터
INSERT INTO warehouses (warehouse_id, warehouse_name, address) VALUES
(10, '서울 물류센터', '서울특별시 강남구 테헤란로'),
(20, '부산 물류센터', '부산광역시 해운대구 센텀중앙로'),
(30, '인천 공항터미널', '인천광역시 중구 공항로');

-- 3. 상품 데이터
INSERT INTO products (product_id, product_name) VALUES
(101, '고성능 노트북'),
(102, '기계식 키보드'),
(103, '4K 모니터');

-- 4. 화물 데이터 (2개의 화물 생성)
INSERT INTO shipments (shipment_id, company_id, origin_warehouse_id, destination_warehouse_id, created_at) VALUES
(1001, 1, 10, 20, '2025-09-26 09:00:00'), -- FastLogi, 서울 -> 부산
(1002, 2, 20, 10, '2025-09-27 11:00:00'); -- QuickCommerce, 부산 -> 서울

-- 5. 화물별 상품 데이터
INSERT INTO shipment_items (shipment_id, product_id, quantity) VALUES
(1001, 101, 2),  -- 화물 1001번은 노트북 2개
(1001, 102, 5),  -- 키보드 5개
(1002, 103, 10); -- 화물 1002번은 모니터 10개

-- 6. 화물 상태 변경 이력 데이터 (5건의 초기 로그)
INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES
(1001, '주문접수', '고객사 시스템 연동 완료', '2025-09-26 09:00:00'),
(1001, '집화완료', '서울센터에서 상품 인수', '2025-09-26 14:30:00'),
(1001, '터미널간이동', '서울 -> 부산 간선차량 출발', '2025-09-26 23:00:00'),
(1001, '배송중', '부산 배송기사에게 인계됨', '2025-09-27 08:15:00'),
(1002, '주문접수', '고객사 요청 확인', '2025-09-27 11:00:00');