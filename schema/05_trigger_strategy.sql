-- =============================================================================
-- LogisFlow Q3 전략 2: DB 트리거 (Database Trigger)
-- =============================================================================
--
-- 📌 목적:
--    shipment_updates 테이블에 INSERT가 발생하면,
--    자동으로 shipments 테이블의 current_status와 last_updated_at을 동기화
--
-- 📌 장점:
--    - 애플리케이션 코드 단순화 (INSERT만 하면 됨)
--    - 데이터 정합성 보장 (DB 레벨에서 트랜잭션 보장)
--
-- 📌 단점:
--    - DB가 계산/처리 부하를 담당 (Scaling 어려움)
--    - 로직이 숨겨져 있어 디버깅이 어려울 수 있음
--
-- =============================================================================

-- 1. 트리거 함수 정의
CREATE OR REPLACE FUNCTION update_shipment_status_trigger()
RETURNS TRIGGER AS $$
BEGIN
    -- shipments 테이블 업데이트
    -- NEW: 새로 INSERT된 shipment_updates 행
    UPDATE shipments
    SET 
        current_status = NEW.status_code,
        last_updated_at = NEW.timestamp
    WHERE shipment_id = NEW.shipment_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. 트리거 생성
-- 파티션 테이블의 경우, PostgreSQL 13+ 에서는 부모 테이블에 트리거를 걸면 자식 파티션에도 적용됨
DROP TRIGGER IF EXISTS trg_update_shipment_status ON shipment_updates;

CREATE TRIGGER trg_update_shipment_status
AFTER INSERT ON shipment_updates
FOR EACH ROW
EXECUTE FUNCTION update_shipment_status_trigger();

-- =============================================================================
-- 안내
-- =============================================================================
-- 이 트리거는 기본적으로 비활성화 상태로 두거나, 
-- API에서 전략 2(trigger)를 사용할 때만 의존해야 합니다.
-- 
-- 하지만 PostgreSQL 트리거는 조건부 실행(WHEN)을 동적으로 제어하기 어렵고,
-- 전역적으로 동작하므로 전략 1(Application Sync)과 충돌할 수 있습니다.
-- 
-- ★ 실험을 위한 조치:
-- 실제 실험 시에는 전략 1 테스트 후 트리거를 생성하고 전략 2를 테스트하거나,
-- 전략 1 테스트 시 중복 업데이트를 허용하는 방식으로 진행합니다.
-- (여기서는 단순히 트리거를 생성해두고 동작을 확인합니다.)
