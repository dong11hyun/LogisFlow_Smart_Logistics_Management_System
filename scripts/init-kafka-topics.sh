#!/bin/bash
# =============================================================================
# LogisFlow Kafka 토픽 초기화 스크립트
# =============================================================================
#
# 📌 사용법:
#   Windows: docker exec -it logisflow-kafka bash /scripts/init-kafka-topics.sh
#   또는 직접 아래 명령어 실행
#
# 📌 토픽 목록:
#   - shipment-status-updates: Q3 전략 3(비동기) 상태 변경 이벤트
#
# =============================================================================

KAFKA_BOOTSTRAP=localhost:9092

echo "🚀 LogisFlow Kafka 토픽 초기화 시작..."

# -----------------------------------------------------------------------------
# 토픽 1: shipment-status-updates
# -----------------------------------------------------------------------------
# 용도: Q3 전략 3 - 비동기 상태 동기화
# 파티션: 3개 (병렬 처리용)
# 복제본: 1개 (단일 브로커 환경)
# 보존기간: 7일 (168시간)
# -----------------------------------------------------------------------------
echo "📦 토픽 생성: shipment-status-updates"
kafka-topics --bootstrap-server $KAFKA_BOOTSTRAP \
    --create \
    --if-not-exists \
    --topic shipment-status-updates \
    --partitions 3 \
    --replication-factor 1 \
    --config retention.ms=604800000

# -----------------------------------------------------------------------------
# 토픽 2: shipment-updates-es (Q4용 - Elasticsearch 동기화)
# -----------------------------------------------------------------------------
echo "📦 토픽 생성: shipment-updates-es"
kafka-topics --bootstrap-server $KAFKA_BOOTSTRAP \
    --create \
    --if-not-exists \
    --topic shipment-updates-es \
    --partitions 3 \
    --replication-factor 1 \
    --config retention.ms=604800000

# -----------------------------------------------------------------------------
# 토픽 목록 확인
# -----------------------------------------------------------------------------
echo ""
echo "✅ 생성된 토픽 목록:"
kafka-topics --bootstrap-server $KAFKA_BOOTSTRAP --list

echo ""
echo "🎉 Kafka 토픽 초기화 완료!"
