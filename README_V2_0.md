# LogisFlow: 대규모 물류 처리 시스템의 성능 최적화 프로젝트
---

## 🔹 목차

1. [문제 지문 (Scenario)](#-문제-지문-scenario)
2. [과제 질문 & 해결 전략 (5가지)](#과제-질문--해결-전략-5가지)
3. [상황 개요](#상황-개요)
4. [현재 시스템의 성능 병목](#-현재-시스템의-성능-병목)
5. [최적화 과제](#최적화-과제)
6. [🔹 Quick Start](#-quick-start)
7. [📁 프로젝트 구조](#-프로젝트-구조)
8. [🔹 개념 심층 분석: DB 성능 최적화와 트레이드오프](#-개념-심층-분석-db-성능-최적화와-트레이드오프)
9. [🔹 구현 현황](#-구현-현황)
10. [🔹 향후 확장 및 개선 계획 (Future Plans)](#-향후-확장-및-개선-계획-future-plans)

---

##  문제 지문 (Scenario)

당신은 B2B 스마트 물류 플랫폼 **'Logis-Flow'**의 백엔드 수석 엔지니어입니다.
서비스가 폭발적으로 성장하며 하루 수백만 건의 물류 이동이 발생하자, 핵심 기능인 **'실시간 화물 추적 대시보드'**에서 심각한 성능 저하가 발생했습니다.

[🔷상황 개요](#-상황-개요)
초기 데이터베이스는 엄격한 제 3 정규형(3NF)을 준수하여 설계되었으나, 500억 건의 로그 테이블(`shipment_updates`)에서 최신 상태를 조회하는 과정이 시스템의 병목이 되었습니다.

[🔷현재 시스템의 성능 병목](#-현재-시스템의-성능-병목)
이러한 문제를 해결하기 위해,
- **데이터베이스 비정규화**를 통한 읽기 성능 개선,
- **데이터 정합성(Consistency)** 유지 전략 수립,
- 대규모 데이터 처리를 위한 **파티셔닝 및 NoSQL 도입**을 계획해야 합니다.

---

## 과제 질문 & 해결 전략 (5가지)

### 질문 1: 병목의 근본 원인 분석
- 현재 스키마에서 대시보드 로딩 시 발생하는 `Top-N Query` (특정 그룹별 최신 1건 조회)의 성능 문제 원인을 인덱스 구조와 스캔 범위 관점에서 분석하시오.
- [과제 1: 병목 원인 분석](#과제-1-병목-원인-분석---top-n-query의-비효율성)

**[답변]**
> **최신 상태 조회(Top-N Query, Limit 1)의 비효율성**:
> 500억 건의 테이블에서 `shipment_id`별 가장 최신(`ORDER BY timestamp DESC LIMIT 1`) 데이터를 찾는 것은 매우 고비용입니다.
> 1. **Loose Index Scan 부하**: (shipment_id, timestamp) 복합 인덱스가 있더라도, 목록 조회 시 N개의 화물 각각에 대해 인덱스 트리를 탐색(Index Seek)해야 합니다. 워낙 데이터가 많아 인덱스 깊이(Height)가 깊고, 랜덤 I/O가 폭증합니다.
> 2. **Aggregate 부하**: `GROUP BY` 후 `MAX(timestamp)`를 수행하면 인덱스를 타더라도 광범위한 데이터를 스캔해야 하므로 CPU와 I/O를 소진합니다.

### 질문 2: 비정규화 전략 제시
- 조인 연산과 실시간 집계 작업을 최소화하기 위한 논리적인 스키마 변경안(비정규화)을 제안하시오.
- [과제 2: 비정규화 전략](#과제-2-비정규화-전략---read-성능-극대화)

**[답변]**
> **Current State Pattern 적용**:
> `shipments` 테이블에 다음 컬럼을 추가하여 `shipment_updates` 테이블 조인을 제거합니다.
> - `current_status_code`: 가장 최근 상태 코드
> - `last_updated_at`: 가장 최근 업데이트 시간
> - `origin/destination_warehouse_name`: 창고 조인 제거
>
> 이를 통해 500억 건 테이블 조회 없이 `shipments` 테이블만으로 대시보드를 렌더링할 수 있습니다. (벤치마크 결과 23초 -> 0.00초 단축)

### 질문 3: 새로운 트레이드오프 분석 (정합성 유지)
- 비정규화로 인해 발생한 데이터 중복 문제를 해결하기 위해, 쓰기 시점의 동기화 전략(트랜잭션 vs 트리거 vs 메시지 큐) 3가지를 비교하고 구현하시오.
- [과제 3: 정합성 유지 전략](#과제-3-정합성-유지-전략---consistency-trade-offs)

**[답변]**
> **1. 동기적 애플리케이션 트랜잭션**: 완벽한 정합성을 보장하지만 DB Lock 점유로 쓰기 성능이 저하됩니다.
> **2. 데이터베이스 트리거**: 앱 코드 수정 없이 적용 가능하지만, DB에 부하를 숨기게 되어 유지보수와 확장에 불리합니다.
> **3. 메시지 큐(Async) - 권장**: `shipments` 갱신을 Kafka/RabbitMQ 등을 통해 비동기로 처리합니다. '최종 일관성(Eventual Consistency)' 모델로, 사용자 응답이 가장 빠르고 DB 부하를 분산할 수 있습니다.

### 질문 4: 아키텍처적 접근 (파티셔닝 & NoSQL)
- 이력 데이터(`shipment_updates`) 조회를 최적화하기 위해 RDB 파티셔닝과 NoSQL 이관 전략을 비교하시오.
- [과제 4: 대용량 데이터 아키텍처](#과제-4-대용량-데이터-아키텍처---partitioning-vs-nosql)

**[답변]**
> **RDB 파티셔닝**: `timestamp` 기준 월별 파티셔닝을 통해 최근 데이터 조회 속도를 유지하고 오래된 데이터 관리를 효율화합니다.
> **NoSQL 이관 (DynamoDB/Elasticsearch)**: `shipment_id`를 파티션 키로 사용하여 수십억 건 데이터에서도 O(1) 수준의 조회 성능을 보장하고, 컴퓨팅 자원을 RDB와 분리합니다.

### 질문 5: 데이터 생명주기 관리 (ILM)
- 법적 요구사항과 비용을 고려한 장기 데이터 보관 전략을 수립하시오.
- [과제 5: 데이터 수명주기 관리](#과제-5-데이터-수명주기-관리-ilm)

**[답변]**
> **Tiered Storage 전략**:
> - **HOT (운영 DB)**: 최근 3~6개월 데이터. 고성능 SSD.
> - **WARM (Data Lake)**: 1년 이내 데이터. 조회 가능한 S3(Athena) 또는 저렴한 NoSQL.
> - **COLD (Glacier)**: 3~5년 지난 법적 보관 데이터. 압축 후 S3 Glacier Deep Archive 저장 (최저 비용).

---

## 상황 개요

**'Logis-Flow'** - 초거대 물류 처리 플랫폼

### 핵심 엔티티 및 스키마 구조
| 테이블 | 설명 | 데이터 규모 |
|--------|------|------------|
| `shipments` | 화물 정보 | 5억 건 |
| `companies` | 고객사 정보 | 1만 건 |
| `warehouses` | 창고 정보 | 5만 건 |
| `products` | 상품 마스터 | 1천만 건 |
| `shipment_items` | 화물-상품 관계 | 50억 건 |
| `shipment_updates` | 상태 변경 로그 (Append-only) | **500억 건** |

---

## 🚨 현재 시스템의 성능 병목

### 1. 로그 테이블의 폭발적 증가
- 모든 상태 변경이 `shipment_updates`에 쌓이면서 테이블 크기가 감당 불가능한 수준으로 증가 (500억 Row).

### 2. 대시보드 로딩 지연 (10초 이상)
- 단순 목록 조회를 위해 `shipment_updates` 테이블을 `GROUP BY` 하거나 Subquery로 `ORDER BY ... LIMIT 1`을 수행해야 함.
- Read Replica의 CPU가 100%를 치는 상황 발생.

---

## 🔹 Quick Start

```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
# Windows
venv\Scripts\activate 
# macOS/Linux
source venv/bin/activate

# 2. 패키지 설치
pip install -r requirements.txt
# (pymysql, faker 등 필요)

# 3. 데이터베이스 생성 및 시드 데이터 적재 (MySQL/PostgreSQL)
# (README.md의 SQL 명령어 참고)
mysql -u root -p < schema/01_schema_ddl.sql
...

# 4. 정규화 vs 비정규화 성능 벤치마크 실행
python "benchmark_v1(정규화_비정규화).py"
python "benchmark_v2(인덱스_비정규화).py"

# 5. 정합성 전략(Sync/Trigger/Async) 트레이드오프 테스트 실행
python consistency_test.py
```

---

## 📁 프로젝트 구조

```
LogisFlow/
├── schema/                     # DB 스키마 및 더미 데이터 SQL
│   ├── 01_schema_ddl.sql
│   ├── post_01_schema_ddl.sql  # PostgreSQL 버전
│   └── ...
├── benchmark_v1(...).py        # 정규화 vs 비정규화 성능 비교
├── benchmark_v2(...).py        # 인덱스 최적화 vs 비정규화 비교
├── consistency_test.py         # 🔺 [핵심] 3가지 정합성 전략 구현 및 검증
├── faker_to_mysql.py           # 대용량 테스트 데이터 생성기
├── data_cleaner.py             # 데이터 정리 유틸리티
├── README.md                   # V1 문서 (DB 성능 비교 중심)
├── (1회차)Infra_Backend.md     # 문제 정의 및 과제 설명서
└── 참고.md.md                  # 문서 양식 가이드
```

---

## 📚 개념 심층 분석: DB 성능 최적화와 트레이드오프

### 정규화의 함정과 비정규화의 필요성
제 3 정규형은 데이터 중복을 제거하여 이상 현상(Anomaly)을 방지하지만, 조회 시 많은 조인(JOIN)과 연산을 요구합니다. 특히 Logis-Flow와 같이 **쓰기보다 읽기(조회)가 압도적으로 많고, 최신 상태 조회가 빈번한 시스템**에서는 정규화된 구조가 성능의 발목을 잡습니다. **반정규화(Denormalization)**는 데이터 중복을 허용하는 대신 조회 성능을 극대화하는 기법으로, 이 프로젝트에서는 `current_status` 컬럼을 추가함으로써 수백억 건 테이블 스캔을 O(1) 조회로 단축시켰습니다.

### CAP 이론과 정합성 모델 선택
비정규화는 필연적으로 데이터 불일치(Inconsistency) 위험을 수반합니다. 우리는 CAP 이론(Consistency, Availability, Partition Tolerance)에서 완벽한 C를 포기하고 A와 P를 취하는 전략을 선택했습니다.
- `consistency_test.py`에서 구현한 **Async Queue 전략**은 **최종 일관성(Eventual Consistency)** 모델입니다.
- 사용자는 아주 잠시동안 과거의 상태를 볼 수도 있지만(지연), 시스템은 응답성을 유지하고 결코 멈추지 않습니다. 이는 대규모 트래픽 환경에서 필수적인 타협입니다.

---

## 🔹 구현 현황

이 프로젝트는 현재 다음 단계까지 구현되었습니다:

- [x] **대용량 DB 스키마 설계**: MySQL/PostgreSQL 3NF 스키마 구축
- [x] **테스트 데이터 생성**: Faker를 이용한 수십만 건의 더미 데이터 적재
- [x] **성능 벤치마킹**: 
  - 정규화 테이블(`GROUP BY`, `Subquery`) vs 비정규화 테이블(`Current Column`) 성능 비교
  - 인덱스 유무에 따른 성능 차이 검증
- [x] **정합성 유지 전략 구현 (`consistency_test.py`)**:
  - Strategy A: 동기 트랜잭션 (Strong Consistency)
  - Strategy B: DB Trigger
  - Strategy C: Async Queue (Eventual Consistency)

---

## 🔹 향후 확장 및 개선 계획 (Future Plans)

현재는 단일 DB 인스턴스에서의 성능 최적화와 논리적 설계를 검증했습니다.
차후 스케일 아웃(Scale-out)과 운영 안정성을 위해 다음 단계가 진행될 예정입니다.

### 1. 샤딩(Sharding) 및 파티셔닝(Partitioning) 적용
- **현황**: 단일 테이블에 모든 데이터 저장.
- **계획**: 
  - `shipment_updates` 테이블을 월 단위(Range Partitioning)로 분리.
  - 고객사 ID(`company_id`)를 기준으로 DB 샤딩을 적용하여 수평적 확장.

### 2. NoSQL 이관 (Polyglot Persistence)
- **현황**: 관계형 데이터베이스(RDB)만 사용.
- **계획**: 
  - 로그성 데이터(`shipment_updates`)는 **Elasticsearch**나 **Cassandra**로 이관하여 쓰기 성능 확보 및 시계열 분석 용이성 증대.
  - 화물 상태 캐싱을 위해 **Redis** 도입.

### 3. 메시지 큐 인프라 구축
- **현황**: Python `queue` 모듈을 사용한 인메모리 에뮬레이션.
- **계획**: 
  - 실제 **RabbitMQ** 또는 **kafka** 클러스터를 연동하여 서비스 간 결합도를 낮추고 비동기 처리의 내구성을 보장.

### 4. 데이터 아카이빙 자동화
- **계획**: AWS Glue/Athena를 활용하여 Cold 데이터를 S3 Glacier로 자동 이관하고, 필요 시 쿼리할 수 있는 파이프라인 구축.
