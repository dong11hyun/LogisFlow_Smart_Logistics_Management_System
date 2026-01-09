# LogisFlow 실행 청사진 (Project Blueprint)

이 문서는 `README.md`의 **5가지 핵심 문제**를 순서대로 해결하기 위한 **실행 계획서**입니다.

---

## 🛠️ 기술 스택 (Tech Stack)
*   **Database**: PostgreSQL 14+ (현재 1,000만 건 적재 완료)
*   **Language**: Python 3.9+ (psycopg2, Faker)
*   **Messaging**: Kafka (Docker) or Python Queue (Simulation)
*   **Tools**: Docker (선택), psql client

---

## ✅ 과제별 실행 계획

### □ 과제 1: 병목 원인 분석 (Normalized Schema)
> **Goal**: 1,000만 건에서 '최신 상태 조회'가 왜 느린지 숫자로 확인.
   □ `benchmark_q1_normalized.py` 작성
   □ 쿼리 실행: `SELECT ... ORDER BY timestamp DESC LIMIT 1` (서브쿼리 방식)
   □ 성능 측정: 평균 응답 시간(Latency) 기록 (목표: > 1초)
   □ `EXPLAIN ANALYZE` 실행하여 **Index Scan Depth** 및 **Random I/O** 확인

### □ 과제 2: 비정규화 전략 (Denormalization)
> **Goal**: 컬럼 추가로 조회 속도 0.01초 달성.
   □ 스키마 변경: `shipments` 테이블에 `current_status`, `last_updated_at` 컬럼 추가
   □ 데이터 마이그레이션: 기존 `shipment_updates`의 최신 값을 `shipments`로 복사 (Update 쿼리)
   □ `benchmark_q2_denormalized.py` 작성 및 실행
   □ **[결과 비교]** Q1(1초) vs Q2(0.001초) 그래프 작성

### □ 과제 3: 정합성 유지 (Consistency)
> **Goal**: 비정규화로 인한 데이터 불일치 문제를 해결하는 3가지 방법 비교.
   □ **[전략 A] 동기 트랜잭션**
      □ 코드 작성: `BEGIN` -> `INSERT log` -> `UPDATE shipment` -> `COMMIT`
      □ 테스트: 동시에 100개 요청 보낼 때 `Lock Wait Timeout` 발생하는지 확인
   □ **[전략 B] DB 트리거**
      □ 코드 작성: PostgreSQL `AFTER INSERT` Trigger Function 생성
      □ 테스트: 대량 Insert 시 DB CPU 부하율 측정
   □ **[전략 C] 메시지 큐 (Eventual Consistency) - ★최종 선택★**
      □ 코드 작성: Python `Queue` 활용 Producer/Consumer 패턴 구현
      □ (심화) Docker로 **Kafka** 띄우고 연동
      □ 테스트: DB 쓰기 지연(`sleep 0.1`) 상황에서도 사용자 응답은 즉시 반환됨을 증명

### □ 과제 4: 이력 조회 최적화 (Partitioning)
> **Goal**: 1,000만 건 로그 테이블을 날짜별로 쪼개서 검색 효율 극대화.
   □ 파티션 테이블 설계: `shipment_updates_partitioned` (PARTITION BY RANGE)
   □ 데이터 이관: 기존 1,000만 건 데이터를 파티션 테이블로 `INSERT INTO ... SELECT`
   □ 검증 쿼리: `EXPLAIN SELECT ... WHERE timestamp = '2024-01-01'`
   □ **[결과 확인]** "Partition Pruning" 발생 여부 (전체가 아닌 1개 파티션만 스캔했는가?)

### □ 과제 5: 데이터 생명주기 (ILM)
> **Goal**: 오래된 데이터를 돈 안 드는 파일로 바꾸고 DB에서 삭제.
   □ `ilm_manager.py` 작성
   □ 정책 설정: "어제 날짜 데이터는 Cold Data로 간주"
   □ 아카이빙 실행: 파티션 Detach -> `COPY TO 'archive.csv'` -> `DROP TABLE`
   □ 검증: DB 용량 감소 및 파일 생성 확인
