-- =============================================================================
-- LogisFlow Q4 방안 1: 파티션 테이블 구성
-- =============================================================================
--
-- 📌 목적:
--    shipment_updates 테이블을 월별로 파티셔닝하여 조회 성능 최적화
--    500억 건 → 월별 분리 → 특정 기간만 스캔
--
-- 📌 사용법:
--    이 스크립트는 기존 shipment_updates 테이블을 파티션 테이블로 재구성합니다.
--    주의: 기존 데이터가 있으면 마이그레이션 필요!
--
-- 📌 파티션 전략:
--    - 파티션 키: timestamp (상태 변경 시간)
--    - 파티션 단위: 월별 (RANGE)
--    - 예: 2025년 1월 데이터 → shipment_updates_2025_01
--
-- 📌 Q5 ILM과의 연계:
--    오래된 파티션(예: 2년 전)은 DROP 또는 S3 아카이빙 가능
-- =============================================================================

-- 기존 테이블 백업 (데이터가 있는 경우)
-- CREATE TABLE shipment_updates_backup AS SELECT * FROM shipment_updates;

-- 기존 테이블 삭제 (CASCADE로 의존성 함께 제거)
DROP TABLE IF EXISTS shipment_updates CASCADE;

-- =============================================================================
-- 파티션 부모 테이블 생성
-- =============================================================================
CREATE TABLE shipment_updates (
    update_id BIGSERIAL,
    shipment_id INT NOT NULL,
    status_code VARCHAR(50) NOT NULL,
    notes VARCHAR(255),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 파티션 테이블은 PK에 파티션 키(timestamp)를 포함해야 함
    PRIMARY KEY (update_id, timestamp)
    
    -- 주의: 파티션 테이블에서는 FK 제약조건 사용에 주의 필요
    -- PostgreSQL 11+에서는 파티션 테이블의 FK가 지원되지만,
    -- 성능을 위해 애플리케이션 레벨에서 관리하는 것을 권장
) PARTITION BY RANGE (timestamp);

COMMENT ON TABLE shipment_updates IS '화물 상태 변경 로그 (월별 파티셔닝 적용)';

-- =============================================================================
-- 2024년 월별 파티션 생성
-- =============================================================================
CREATE TABLE shipment_updates_2024_01 PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
    
CREATE TABLE shipment_updates_2024_02 PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
    
CREATE TABLE shipment_updates_2024_03 PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
    
CREATE TABLE shipment_updates_2024_04 PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
    
CREATE TABLE shipment_updates_2024_05 PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
    
CREATE TABLE shipment_updates_2024_06 PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
    
CREATE TABLE shipment_updates_2024_07 PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
    
CREATE TABLE shipment_updates_2024_08 PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
    
CREATE TABLE shipment_updates_2024_09 PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
    
CREATE TABLE shipment_updates_2024_10 PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
    
CREATE TABLE shipment_updates_2024_11 PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
    
CREATE TABLE shipment_updates_2024_12 PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- =============================================================================
-- 2025년 월별 파티션 생성
-- =============================================================================
CREATE TABLE shipment_updates_2025_01 PARTITION OF shipment_updates
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
    
CREATE TABLE shipment_updates_2025_02 PARTITION OF shipment_updates
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
    
CREATE TABLE shipment_updates_2025_03 PARTITION OF shipment_updates
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
    
CREATE TABLE shipment_updates_2025_04 PARTITION OF shipment_updates
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
    
CREATE TABLE shipment_updates_2025_05 PARTITION OF shipment_updates
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
    
CREATE TABLE shipment_updates_2025_06 PARTITION OF shipment_updates
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
    
CREATE TABLE shipment_updates_2025_07 PARTITION OF shipment_updates
    FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
    
CREATE TABLE shipment_updates_2025_08 PARTITION OF shipment_updates
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
    
CREATE TABLE shipment_updates_2025_09 PARTITION OF shipment_updates
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
    
CREATE TABLE shipment_updates_2025_10 PARTITION OF shipment_updates
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
    
CREATE TABLE shipment_updates_2025_11 PARTITION OF shipment_updates
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
    
CREATE TABLE shipment_updates_2025_12 PARTITION OF shipment_updates
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- =============================================================================
-- 2026년 월별 파티션 생성 (현재 연도)
-- =============================================================================
CREATE TABLE shipment_updates_2026_01 PARTITION OF shipment_updates
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
    
CREATE TABLE shipment_updates_2026_02 PARTITION OF shipment_updates
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
    
CREATE TABLE shipment_updates_2026_03 PARTITION OF shipment_updates
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
    
CREATE TABLE shipment_updates_2026_04 PARTITION OF shipment_updates
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
    
CREATE TABLE shipment_updates_2026_05 PARTITION OF shipment_updates
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
    
CREATE TABLE shipment_updates_2026_06 PARTITION OF shipment_updates
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
    
CREATE TABLE shipment_updates_2026_07 PARTITION OF shipment_updates
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
    
CREATE TABLE shipment_updates_2026_08 PARTITION OF shipment_updates
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
    
CREATE TABLE shipment_updates_2026_09 PARTITION OF shipment_updates
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
    
CREATE TABLE shipment_updates_2026_10 PARTITION OF shipment_updates
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
    
CREATE TABLE shipment_updates_2026_11 PARTITION OF shipment_updates
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
    
CREATE TABLE shipment_updates_2026_12 PARTITION OF shipment_updates
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

-- =============================================================================
-- 각 파티션에 인덱스 생성 (자동으로 모든 파티션에 적용됨)
-- =============================================================================
-- 화물별 타임라인 조회 최적화
CREATE INDEX idx_shipment_updates_shipment_timestamp 
    ON shipment_updates (shipment_id, timestamp DESC);

-- 상태 코드별 필터링
CREATE INDEX idx_shipment_updates_status 
    ON shipment_updates (status_code);

-- =============================================================================
-- 테스트 데이터 삽입 (시드 데이터 복원)
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

-- =============================================================================
-- 파티션 확인 쿼리
-- =============================================================================
-- 아래 쿼리로 파티션 상태 확인 가능:
-- SELECT relname, pg_size_pretty(pg_relation_size(oid)) 
-- FROM pg_class 
-- WHERE relname LIKE 'shipment_updates%' 
-- ORDER BY relname;

-- 완료 로그
DO $$
BEGIN
    RAISE NOTICE '✅ 파티션 테이블 생성 완료!';
    RAISE NOTICE '   - 2024년: 12개 월별 파티션';
    RAISE NOTICE '   - 2025년: 12개 월별 파티션';
    RAISE NOTICE '   - 2026년: 12개 월별 파티션';
    RAISE NOTICE '   - 총 36개 파티션 생성됨';
END $$;
