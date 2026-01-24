## LogisFlow 스마트 물류 플랫폼

> **프로젝트 목표**: B2B 물류 플랫폼의 핵심 기술적 과제를 실제 구현 및 벤치마크를 통해 검증  
> **데이터 규모**: shipments ~100만 건, shipment_updates ~300만 건 (월별 36개 파티션)

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                      LogisFlow Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐     ┌──────────────┐     ┌──────────────────┐    │
│  │  Client  │────▶│  FastAPI     │────▶│  PostgreSQL      │    │
│  │          │     │  (Backend)   │     │  (파티션 테이블)   │    │
│  └──────────┘     └──────┬───────┘     └──────────────────┘    │
│                          │                                       │
│                          ▼                                       │
│                   ┌──────────────┐                              │
│                   │    Kafka     │                              │
│                   │   (비동기)    │                              │
│                   └──────┬───────┘                              │
│                          │                                       │
│                          ▼                                       │
│                   ┌──────────────┐     ┌──────────────────┐    │
│                   │   Consumer   │────▶│  Elasticsearch   │    │
│                   │              │     │  (이력 검색)       │    │
│                   └──────────────┘     └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 프로젝트 구조

```
B3_LogisFlow/
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI 앱 + Kafka 라이프사이클
│       ├── config.py                # 설정
│       ├── database.py              # DB 연결
│       ├── models.py                # SQLAlchemy 모델
│       ├── schemas.py               # Pydantic 스키마
│       ├── kafka_producer.py        # Q3 Producer
│       ├── kafka_consumer.py        # Q3 Consumer + ES 동기화
│       ├── elasticsearch_client.py  # Q4 ES 클라이언트
│       └── routers/
│           ├── shipments.py         # Q3/Q4 API
│           └── health.py
├── schema/
│   ├── 01_schema.sql                # 비정규화 스키마
│   ├── 02_indexes.sql               # 인덱스
│   ├── 03_seed_data.sql             # 시드 데이터
│   ├── 04_partitioned_schema.sql    # Q4 파티션 테이블
│   └── 05_trigger_strategy.sql      # Q3 트리거
├── scripts/
│   ├── benchmark_q3.py              # Q3 벤치마크
│   ├── benchmark_q4.py              # Q4 벤치마크
│   ├── setup_elasticsearch.py       # ES 초기화
│   └── migrate_to_elasticsearch.py  # PG→ES 마이그레이션
├── data_generator/
│   └── generate_10m.py              # 대용량 데이터 생성
└── docker-compose.yml               # 인프라 구성
```

---

## 🚀 실행 가이드

### 1. 인프라 시작
```powershell
docker-compose up -d
```

### 2. 백엔드 서버 실행
```powershell
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

### 3. API 문서 확인
브라우저: http://localhost:8000/docs

---

## 데이터베이스 설계 심층 탐구: 초거대 물류 플랫폼의 성능 병목 해결

### 상황
당신은 B2B 스마트 물류 플랫폼 'Logis-Flow'의 백엔드 수석 엔지니어로 합류했습니다. Logis-Flow 는 여러 고객사(화주, 운송사)의 상품 입고부터 창고 관리, 최종 목적지 배송까지 전 과정을 추적하고 관리하는 SaaS 솔루션입니다. 서비스 초기, 데이터베이스는 데이터 정합성과 확장성을 최우선으로 고려하여 제 3 정규형을 철저히 준수하여 설계되었습니다.

서비스가 폭발적으로 성장하며 하루에 수백만 건의 물류 이동이 발생하자, 시스템의 핵심 기능인 '실시간 화물 추적 대시보드'에서 심각한 성능 문제가 발생하기 시작했습니다. 이 대시보드는 고객사가 특정 화물(Shipment)의 현재 상태를 한눈에 파악하는 가장 중요한 화면입니다. 이 화면을 렌더링하기 위해 시스템은 다음과 같은 정보를 조합해야 합니다.

- 화물의 고유 ID, 출발 창고 이름, 도착 창고 주소
- 화물의 현재 상태(예: '집화 완료', '터미널 간 이동 중', '배송 중')와 최종 업데이트 시각
- 화물에 포함된 모든 상품의 이름과 수량
- 해당 화물이 생성된 이후 발생한 모든 상태 변경 이력(타임라인)

시스템의 데이터베이스 스키마는 다음과 같이 정규화되어 있습니다.
- `companies`: 고객사 정보 (약 1 만 개)
- `warehouses`: 창고 정보, 주소 포함 (약 5 만 개)
- `products`: 상품 마스터 정보 (약 1 천만 개)
- `shipments`: 화물 정보. origin_warehouse_id, destination_warehouse_id 를 외래 키로 가짐 (누적 5 억 건)
- `shipment_items`: shipments 와 products 를 잇는 다대다 관계 테이블 (누적 50 억 건)
- `shipment_updates`: 모든 화물의 상태 변경 기록이 append-only 방식으로 저장되는 로그 테이블. shipment_id, status_code, timestamp, notes 등의 컬럼을 가짐 (누적 500 억 건)

대시보드 로딩 시, 단일 화물 정보를 조회하는 쿼리는 shipments 테이블을 시작으로 warehouses 테이블을 두 번 조인하고, shipment_items 와 products 를 조인합니다. 가장 치명적인 부분은 화물의 '현재 상태'를 가져오기 위해 500 억 건의 shipment_updates 테이블에서 특정 shipment_id 에 해당하는 기록 중 timestamp 가 가장 최신인 1 건을 찾아야 한다는 점입니다. 또한, 상태 변경 이력 타임라인을 보여주기 위해 해당 shipment_id 의 모든 기록을 timestamp 순으로 정렬해야 합니다.

이 복합적인 쿼리는 피크 시간대에 10 초 이상 소요되어 고객의 불만을 야기하고 있으며, 데이터베이스의 읽기 전용 복제본(Read Replica) 마저 CPU 사용률이 100%에 달하는 상황을 만들고 있습니다.

---

### Q1. 병목의 근본 원인 분석

현재의 정규화된 스키마가 왜 이토록 심각한 읽기 성능 저하를 유발하는지 데이터베이스의 내부 동작 원리와 연관 지어 분석하시오.

> **[답변]**
> 
> **최신 상태 조회(Top-N Query, Limit 1)의 비효율성:**
> 500억 건의 테이블에서 `shipment_id`별 가장 최신(`ORDER BY timestamp DESC LIMIT 1`) 데이터를 찾는 것은 매우 고비용입니다.
>
> - **인덱스 스캔 부하:** (shipment_id, timestamp) 복합 인덱스가 있더라도, 목록 조회 시 N개의 화물 각각에 대해 인덱스 트리를 탐색(Index Seek)해야 합니다. 이를 **Loose Index Scan**이라고 하는데, 데이터 건수가 워낙 많아 인덱스 트리의 깊이(Height)가 깊고, 이로 인해 랜덤 I/O가 폭증합니다.
> - **Aggregate 부하:** 만약 `GROUP BY shipment_id` 후 `MAX(timestamp)`를 수행한다면, 인덱스를 타더라도 엄청난 범위의 데이터를 스캔해야 하므로 CPU와 I/O를 모두 소진하게 됩니다.
>
> **📌 인덱스 트리 탐색 메커니즘:**
> ```
> B+Tree (500억 건, 높이 5~6)
> ┌─────────────────────────────────────────┐
> │  Root → Branch → ... → Leaf (5~6 레벨)  │
> │  각 shipment_id마다 이 탐색을 반복       │
> └─────────────────────────────────────────┘
> 
> 화물 20건 조회 시 = 인덱스 탐색 20회 × 5~6 I/O = 100~120 Random I/O
> ```
> - **인덱스 탐색 → 테이블 조회 (2단계):** 인덱스에서 PK를 찾은 후, 실제 데이터 테이블에서 row를 가져오는 Table Lookup이 추가 발생
> - **조인 시 실행 순서:** Driving 테이블 스캔 → 각 row마다 Inner 테이블 인덱스 탐색 → 결과 결합 (Nested Loop Join)
>
> **📌 왜 실제로 부하가 되는가?**
> - **단일 요청:** 100 Random I/O × 0.1ms(SSD) = ~10ms → 체감상 빠름
> - **동시 1,000명:** 1,000명 × 100 I/O = **100,000 IOPS** → NVMe SSD 한계(~100K IOPS) 도달
> - **캐시 미스:** 500억 건은 메모리에 안 들어감 → 디스크 접근 빈발 → 지연 폭증
>
> **→ 해결책:** `current_state` 스냅샷으로 인덱스 탐색 5~6레벨 → 1레벨, Random I/O 100회 → 20회로 감소

---

### Q2. 비정규화 전략 제시

shipments 테이블의 구조를 어떻게 변경하여 대시보드 로딩에 필요한 조인 연산과 실시간 집계 작업을 최소화할 수 있을지 설명해야 합니다.

> **[답변]**
> 
> 대시보드 목록 조회 시 `JOIN`과 `Subquery`를 제거하는 방향으로 `shipments` 테이블을 비정규화합니다.
>
> **`shipments` 테이블 추가 컬럼:**
> - `current_status` (VARCHAR): 가장 최근 상태 코드를 바로 조회
> - `last_updated_at` (TIMESTAMP): 가장 최근 업데이트 시간
> - `origin_warehouse_name`, `destination_warehouse_name` (VARCHAR): 창고명을 바로 표시하여 2번의 JOIN 제거
>
> **✅ 실제 구현 (schema/01_schema.sql):**
> ```sql
> CREATE TABLE shipments (
>     shipment_id SERIAL PRIMARY KEY,
>     company_id INT,
>     origin_warehouse_id INT,
>     destination_warehouse_id INT,
>     created_at TIMESTAMP,
>     -- 비정규화 컬럼 --
>     current_status VARCHAR(50),
>     last_updated_at TIMESTAMP,
>     origin_warehouse_name VARCHAR(100),
>     destination_warehouse_name VARCHAR(100)
> );
> ```
> 
> 이제 500억 건 테이블을 뒤질 필요 없이, `shipments` 테이블만 조회하면 현재 상태를 즉시 알 수 있습니다.

---

### Q3. 쓰기 정합성 유지 전략 비교

비정규화 전략은 쓰기 경로의 복잡성을 증가시키고 데이터 정합성을 해칠 새로운 위험을 내포합니다. 세 가지 서로 다른 아키텍처적 접근법의 장단점을 비교하시오.

> **[답변]**
>
> **1. 동기적 애플리케이션 트랜잭션 (sync)**
> - **방식:** 코드 레벨에서 `INSERT update`와 `UPDATE shipment`를 하나의 트랜잭션으로 묶습니다.
> - **장점:** 데이터 정합성이 완벽하게 보장됩니다.
> - **단점:** DB Lock 점유 시간이 길어져 동시 처리량이 줄어들 수 있습니다.
>
> **2. 데이터베이스 트리거 (trigger)**
> - **방식:** `shipment_updates` 테이블에 `AFTER INSERT` 트리거를 걸어 DB가 자동으로 `shipments`를 업데이트하도록 합니다.
> - **장점:** 애플리케이션 코드를 수정할 필요가 없습니다.
> - **단점:** DB에 숨겨진 로직이 생겨 유지보수가 어렵고, 대량 INSERT 시 트리거 부하로 DB 성능이 급감할 수 있습니다.
>
> **3. 메시지 큐 비동기 처리 (async) - 추천**
> - **방식:** 상태 변경 요청 시 Kafka를 통해 비동기로 처리합니다.
> - **장점:** 사용자 요청 응답이 가장 빠르고, DB 쓰기 부하를 분산할 수 있습니다.
> - **단점:** 큐 지연 시 잠시동안 상태가 다르게 보일 수 있습니다.

#### ✅ 실제 구현: 5가지 전략 비교

| 전략 | 방식 | API 엔드포인트 |
|:----:|------|----------------|
| sync | 동기 트랜잭션 | INSERT + UPDATE 동시 커밋 |
| trigger | DB 트리거 | INSERT만, 트리거가 UPDATE |
| async | Kafka 비동기 | DB INSERT + Kafka 발행 |
| async_pure | Kafka Only | SELECT + Kafka만 (INSERT 없음) |
| async_fire | Fire-and-Forget | Kafka만 (SELECT도 없음) |

> **비교 기준:** Server Avg Time (순수 서버 처리 시간)

| 규모 | sync | trigger | async | 최적 전략 (개선율) |
|:----:|:----:|:-------:|:-----:|:------------------:|
| **300만** | 13.33ms | **10.47ms** | 10.69ms | trigger (21%↑) |
| **3,000만** | 24.41ms | 22.08ms | **11.97ms** | async (51%↑) |
| **1억** | 16.10ms | 12.45ms | **12.04ms** | async (25%↑) |

> *개선율은 sync 전략(기준) 대비 성능 향상 비율입니다.*

#### 💡 분석 결과

```
📊 규모별 최적 전략 변화

소규모 (300만 건):
   → trigger가 가장 빠름 (10.47ms)
   → 트리거 오버헤드 < UPDATE 직접 처리

중~대규모 (3,000만 ~ 1억 건):
   → async가 가장 빠름 (11.97 ~ 12.04ms)
   → Kafka 비동기 처리로 응답 속도 최적화
   → 데이터 증가 시 trigger/sync는 부하 급증
```

#### ⚠️ 핵심 결론: 규모에 따른 전략 선택

| 전략 | 선택 기준 | 트레이드오프 |
|:----:|----------|-------------|
| **sync** | 정합성 최우선 | 트랜잭션 시간 증가 |
| **trigger** | 소규모 (300만 건 이하) | 대용량 시 부하 증가 |
| **async** | 중~대규모 (3,000만+ 건) | 최종 일관성, 인프라 복잡성 |

> **Q3의 본질:** 트레이드오프를 이해하고 상황에 맞는 전략을 선택하는 것

---

### Q4. 이력 조회 최적화 방안

대시보드의 '상태 변경 이력 타임라인' 기능 최적화를 위해, PostgreSQL 테이블 파티셔닝과 Elasticsearch 도입 방안을 비교하시오.

> **[답변]**
>
> **방안 1: PostgreSQL 테이블 파티셔닝**
> - **내용:** `shipment_updates` 테이블을 `timestamp` 기준(월별)으로 파티셔닝합니다.
> - **장점:** 오래된 데이터가 물리적으로 분리되어, 최근 데이터 조회 시 스캔 범위가 줄어듭니다.
> - **단점:** 여전히 단일 DB 리소스를 사용하므로 부하 분산에 한계가 있습니다.
>
> **방안 2: Elasticsearch 이관**
> - **내용:** 이력 데이터를 `shipment_id`를 기준으로 Elasticsearch로 동기화하여 서비스합니다.
> - **장점:** Key-Value 조회나 시계열 조회에 최적화되어 수십억 건 데이터에서도 일정한 응답 속도를 보장합니다.
> - **단점:** 별도 저장소 비용 및 데이터 동기화 파이프라인 구축 비용이 발생합니다.

#### ✅ 실제 구현

**파티션 테이블 (schema/04_partitioned_schema.sql):**
```sql
CREATE TABLE shipment_updates (
    update_id BIGSERIAL,
    shipment_id INT,
    status_code VARCHAR(50),
    timestamp TIMESTAMP,
    PRIMARY KEY (update_id, timestamp)
) PARTITION BY RANGE (timestamp);

-- 월별 36개 파티션 (2024년 1월 ~ 2026년 12월)
CREATE TABLE shipment_updates_2024_01 PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
-- ...
```

**Elasticsearch 동기화 흐름:**
```
┌─────────────────────────────────────────────────────────────────┐
│                        Write Path                                │
├─────────────────────────────────────────────────────────────────┤
│  API (async)                                                     │
│       ↓                                                          │
│  Kafka Topic: shipment-status-updates                            │
│       ↓                                                          │
│  Kafka Consumer                                                  │
│       ├──────────────────┬──────────────────┐                   │
│       ↓                  ↓                  ↓                   │
│  PostgreSQL INSERT    PostgreSQL UPDATE   Elasticsearch INDEX   │
│  (shipment_updates)   (shipments)         (shipment-updates)    │
└─────────────────────────────────────────────────────────────────┘
```

#### 📊 벤치마크 결과

| Source | TPS | Server Avg | 비교 |
|:------:|:---:|:----------:|:----:|
| **PostgreSQL** | 9.61 | **24.51ms** | 🥇 66% 빠름 |
| Elasticsearch | 9.43 | 72.51ms | 🥈 |

#### 💡 선택 근거

```
✅ 현재 규모(~300만건)에서는 PostgreSQL이 유리
✅ 파티션 프루닝 + 복합 인덱스의 효과가 탁월
✅ Elasticsearch는 10억건+, 풀텍스트 검색 시 도입 권장
```

| 권장 상황 | 저장소 | 이유 |
|----------|:------:|------|
| ~10억건, 단순 조회 | PostgreSQL | 파티션 프루닝 |
| 10억건+, 복합 검색 | Elasticsearch | 분산 처리 |

---

### Q5. 데이터 생명주기 관리

shipment_updates 테이블은 시간이 지남에 따라 무한히 커질 것입니다. 데이터 생명주기 관리 전략을 수립하시오.

> **[답변]**
>
> **데이터 수명 주기(ILM) 전략:**
>
> 1. **HOT 데이터 (운영 DB):** 최근 3~6개월(또는 진행 중인 건) 데이터는 고성능 RDB에 유지하여 즉시 조회 가능하게 합니다.
>
> 2. **WARM 데이터 (NoSQL/Data Lake):** 6개월~1년 지난 데이터는 저렴한 NoSQL이나 조회 가능한 S3(Athena 활용) 영역으로 옮겨 가끔 발생하는 조회 요청을 처리합니다.
>
> 3. **COLD 데이터 (S3 Glacier):** 법적 보관 의무(예: 3~5년)가 있는 데이터는 압축 후 AWS S3 Glacier Deep Archive 같은 최저가 스토리지로 보냅니다. 이는 복구에 시간이 걸리지만 비용이 매우 저렴합니다. 운영 DB에서는 해당 데이터를 삭제(`DELETE` or `DROP PARTITION`)하여 성능을 유지합니다.

#### ✅ 파티션 기반 ILM 장점

월별 파티션 구조(`shipment_updates_2024_01`, `shipment_updates_2024_02`, ...)를 활용하면:
- **빠른 삭제:** `DROP TABLE shipment_updates_2022_01` 한 줄로 수백만 건 삭제 (DELETE보다 1000배 빠름)
- **손쉬운 마이그레이션:** 파티션 단위로 S3로 덤프 후 삭제 가능
- **조회 성능 유지:** 오래된 파티션 삭제 후에도 최신 데이터 조회 성능에 영향 없음

---

## ✅ 프로젝트 완료 항목

- [x] 1단계: 인프라 구축 (Docker Compose - PostgreSQL, Kafka, Elasticsearch, Redis)
- [x] 2단계: 데이터 파이프라인 (파티션 테이블, 비정규화 스키마, 100만 화물 + 300만 로그 생성)
- [x] 3단계: 백엔드 API (FastAPI - 상태 변경 API, 타임라인 조회 API)
- [x] 4단계: Q3 정합성 전략 (5가지 전략 구현 및 벤치마크)
- [x] 5단계: Q4 저장소 비교 (PostgreSQL vs Elasticsearch 벤치마크)
- [x] 6단계: 벤치마크 및 문서화

---

## 🛠️ 기술 스택

| 영역 | 기술 |
|------|------|
| **Backend** | FastAPI, Python, SQLAlchemy |
| **Database** | PostgreSQL (파티션 테이블) |
| **Message Queue** | Apache Kafka |
| **Search Engine** | Elasticsearch |
| **Cache** | Redis |
| **Infrastructure** | Docker, Docker Compose |
