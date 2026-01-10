-- =============================================================================
-- LogisFlow 스마트 물류 플랫폼 - 인덱스 정의
-- =============================================================================
-- 
-- 📌 인덱스 전략:
--    1. 외래 키 컬럼: 조인 성능 향상
--    2. 조회 빈도 높은 컬럼: current_status, timestamp
--    3. 복합 인덱스: shipment_id + timestamp (타임라인 조회용)
--
-- 📌 동료 개발자 참고:
--    - 인덱스는 INSERT 성능을 저하시키므로 벤치마크 시 고려
--    - Q4 파티셔닝 적용 시 파티션별 로컬 인덱스로 자동 분할
-- =============================================================================

-- =============================================================================
-- shipments 테이블 인덱스
-- =============================================================================

-- 고객사별 화물 조회
CREATE INDEX idx_shipments_company_id 
    ON shipments(company_id);

-- 출발/도착 창고별 화물 조회
CREATE INDEX idx_shipments_origin_warehouse 
    ON shipments(origin_warehouse_id);

CREATE INDEX idx_shipments_destination_warehouse 
    ON shipments(destination_warehouse_id);

-- 현재 상태별 화물 조회 (대시보드 필터링)
CREATE INDEX idx_shipments_current_status 
    ON shipments(current_status);

-- 생성일 기준 조회 (최근 화물 목록)
CREATE INDEX idx_shipments_created_at 
    ON shipments(created_at DESC);

-- =============================================================================
-- shipment_updates 테이블 인덱스 ⭐ 성능 핵심
-- =============================================================================

-- 화물별 상태 이력 조회 (타임라인) - 가장 중요한 인덱스
-- Q1에서 언급된 "특정 shipment_id의 기록 중 timestamp가 가장 최신인 1건" 조회 최적화
CREATE INDEX idx_shipment_updates_shipment_timestamp 
    ON shipment_updates(shipment_id, timestamp DESC);

-- 상태 코드별 조회 (통계용)
CREATE INDEX idx_shipment_updates_status_code 
    ON shipment_updates(status_code);

-- 시간 범위 조회 (Q5 ILM 아카이빙용)
CREATE INDEX idx_shipment_updates_timestamp 
    ON shipment_updates(timestamp);

-- =============================================================================
-- shipment_items 테이블 인덱스
-- =============================================================================

-- 상품별 화물 조회 (역조회)
CREATE INDEX idx_shipment_items_product_id 
    ON shipment_items(product_id);

-- 인덱스 생성 완료 로그
DO $$
BEGIN
    RAISE NOTICE '✅ LogisFlow 인덱스 생성 완료!';
    RAISE NOTICE '   - shipments: 5개 인덱스';
    RAISE NOTICE '   - shipment_updates: 3개 인덱스';
    RAISE NOTICE '   - shipment_items: 1개 인덱스';
END $$;
