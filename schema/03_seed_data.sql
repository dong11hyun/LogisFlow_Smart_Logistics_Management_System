-- =============================================================================
-- LogisFlow 스마트 물류 플랫폼 - 초기 시드 데이터
-- =============================================================================
-- 
-- 📌 용도: 개발/테스트용 최소 데이터
--    - 대량 데이터는 data_generator/ 스크립트로 별도 생성
--
-- 📌 데이터 규모:
--    - 회사: 5개
--    - 창고: 10개
--    - 상품: 20개
--    - 화물: 5개 (샘플)
--    - 상태 변경: 15개 (화물당 3개)
-- =============================================================================

-- =============================================================================
-- 1. 고객사 데이터
-- =============================================================================
INSERT INTO companies (company_name) VALUES
    ('삼성전자'),
    ('LG전자'),
    ('현대자동차'),
    ('SK하이닉스'),
    ('네이버');

-- =============================================================================
-- 2. 창고 데이터
-- =============================================================================
INSERT INTO warehouses (warehouse_name, address) VALUES
    ('서울 강남 물류센터', '서울시 강남구 테헤란로 123'),
    ('서울 강서 물류센터', '서울시 강서구 공항대로 456'),
    ('인천 송도 물류센터', '인천시 연수구 송도동 789'),
    ('경기 용인 물류센터', '경기도 용인시 처인구 물류로 111'),
    ('경기 이천 물류센터', '경기도 이천시 마장면 물류단지 222'),
    ('부산 신항 물류센터', '부산시 강서구 신항로 333'),
    ('대구 달성 물류센터', '대구시 달성군 물류센터길 444'),
    ('광주 광산 물류센터', '광주시 광산구 첨단로 555'),
    ('대전 유성 물류센터', '대전시 유성구 엑스포로 666'),
    ('제주 첨단 물류센터', '제주시 첨단로 777');

-- =============================================================================
-- 3. 상품 데이터
-- =============================================================================
INSERT INTO products (product_name) VALUES
    ('스마트폰 Galaxy S24'),
    ('노트북 LG gram'),
    ('무선 이어폰 AirPods Pro'),
    ('스마트워치 Galaxy Watch'),
    ('태블릿 iPad Pro'),
    ('게이밍 마우스 Logitech'),
    ('기계식 키보드 Leopold'),
    ('모니터 27인치 LG'),
    ('외장 SSD 1TB'),
    ('보조배터리 20000mAh'),
    ('USB-C 허브 7포트'),
    ('웹캠 Logitech C920'),
    ('블루투스 스피커 JBL'),
    ('노이즈캔슬링 헤드폰 Sony'),
    ('충전기 65W GaN'),
    ('HDMI 케이블 2m'),
    ('USB 메모리 128GB'),
    ('SD 카드 256GB'),
    ('마우스 패드 XXL'),
    ('노트북 스탠드');

-- =============================================================================
-- 4. 화물 데이터 (샘플 5개)
-- =============================================================================
-- 비정규화 컬럼 (current_status, origin_warehouse_name 등)도 함께 설정
INSERT INTO shipments (
    company_id, 
    origin_warehouse_id, 
    destination_warehouse_id,
    current_status,
    last_updated_at,
    origin_warehouse_name,
    destination_warehouse_name
) VALUES
    (1, 1, 6, 'DELIVERED', NOW() - INTERVAL '1 day', '서울 강남 물류센터', '부산 신항 물류센터'),
    (2, 2, 7, 'IN_TRANSIT', NOW() - INTERVAL '6 hours', '서울 강서 물류센터', '대구 달성 물류센터'),
    (3, 3, 8, 'PICKED_UP', NOW() - INTERVAL '2 hours', '인천 송도 물류센터', '광주 광산 물류센터'),
    (4, 4, 9, 'PENDING', NOW(), '경기 용인 물류센터', '대전 유성 물류센터'),
    (5, 5, 10, 'OUT_DELIVERY', NOW() - INTERVAL '30 minutes', '경기 이천 물류센터', '제주 첨단 물류센터');

-- =============================================================================
-- 5. 화물-상품 연결 데이터
-- =============================================================================
INSERT INTO shipment_items (shipment_id, product_id, quantity) VALUES
    -- 화물 1: 스마트폰, 이어폰
    (1, 1, 100),
    (1, 3, 50),
    -- 화물 2: 노트북, 마우스, 키보드
    (2, 2, 30),
    (2, 6, 30),
    (2, 7, 30),
    -- 화물 3: 태블릿, 충전기
    (3, 5, 80),
    (3, 15, 80),
    -- 화물 4: 모니터, 스탠드
    (4, 8, 20),
    (4, 20, 20),
    -- 화물 5: SSD, USB, SD카드
    (5, 9, 200),
    (5, 17, 500),
    (5, 18, 300);

-- =============================================================================
-- 6. 상태 변경 로그 데이터 (화물당 3개씩)
-- =============================================================================
-- 화물 1: 배송 완료
INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES
    (1, 'PENDING', '주문 접수됨', NOW() - INTERVAL '3 days'),
    (1, 'PICKED_UP', '집화 완료 - 강남센터', NOW() - INTERVAL '2 days'),
    (1, 'DELIVERED', '배송 완료 - 부산 고객사 인수', NOW() - INTERVAL '1 day');

-- 화물 2: 이동 중
INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES
    (2, 'PENDING', '주문 접수됨', NOW() - INTERVAL '1 day'),
    (2, 'PICKED_UP', '집화 완료 - 강서센터', NOW() - INTERVAL '12 hours'),
    (2, 'IN_TRANSIT', '대구 방면 이동 중', NOW() - INTERVAL '6 hours');

-- 화물 3: 집화 완료
INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES
    (3, 'PENDING', '주문 접수됨', NOW() - INTERVAL '8 hours'),
    (3, 'PICKED_UP', '집화 완료 - 송도센터', NOW() - INTERVAL '2 hours');

-- 화물 4: 대기 중
INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES
    (4, 'PENDING', '주문 접수됨 - 오늘 집화 예정', NOW());

-- 화물 5: 배송 출발
INSERT INTO shipment_updates (shipment_id, status_code, notes, timestamp) VALUES
    (5, 'PENDING', '주문 접수됨', NOW() - INTERVAL '2 hours'),
    (5, 'PICKED_UP', '집화 완료 - 이천센터', NOW() - INTERVAL '1 hour'),
    (5, 'OUT_DELIVERY', '제주행 배송 출발', NOW() - INTERVAL '30 minutes');

-- 시드 데이터 삽입 완료 로그
DO $$
BEGIN
    RAISE NOTICE '✅ LogisFlow 시드 데이터 삽입 완료!';
    RAISE NOTICE '   - 회사: 5개';
    RAISE NOTICE '   - 창고: 10개';
    RAISE NOTICE '   - 상품: 20개';
    RAISE NOTICE '   - 화물: 5개';
    RAISE NOTICE '   - 상태 로그: 12개';
END $$;
