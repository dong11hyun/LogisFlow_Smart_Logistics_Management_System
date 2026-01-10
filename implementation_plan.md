# LogisFlow 스마트 물류 플랫폼 - 최종 설계도

---

##  구현 순서 (세분화 버전)

> **총 예상 기간: 14일 (2주)**

### 1단계: 인프라 기반 구축 (2일)

| 순번 | 작업 | 예상 시간 | 근거 |
|:----:|------|:--------:|------|
| 1-1😀 | `docker-compose.yml` 작성 (PG, Kafka, Zookeeper, ES, Redis) | 4h | 모든 서비스의 기반이므로 최우선. 개발 환경 통일 필수 |
| 1-2😀 | PostgreSQL 초기화 스키마 구성 (`01_schema_ddl.sql`) | 2h | API 개발 전 DB 스키마 필요 |
| 1-3😀| Kafka 토픽 생성 및 연결 테스트 (`shipment-status-updates`) | 2h | Q3 전략 3(비동기)에 필수. 연결 검증 선행 |
| 1-4😀 | Elasticsearch 인덱스 설정 (`shipment-updates`) | 2h | Q4 방안 2(NoSQL)에 필수 |
| 1-5 | Docker Compose 통합 테스트 (전체 서비스 `up` 확인) | 2h | 전체 연결 검증 후 다음 단계 진행 가능 |

### 2단계: 데이터 파이프라인 (2일)

| 순번 | 작업 | 예상 시간 | 근거 |
|:----:|------|:--------:|------|
| 2-1 | 비정규화 스키마 설계 (`current_status`, `last_updated_at` 등) | 2h | README Q2 답변 구현. 성능 테스트의 핵심 |
| 2-2 | 파티션 테이블 구성 (`02_partitioned_schema.sql`) | 4h | Q4 방안 1(파티셔닝) 구현. 월별 파티션 자동 생성 |
| 2-3 | 천만 건 데이터 생성기 개선 (`data_generator/generate_10m.py`) | 4h | 벤치마크용 대용량 데이터. 병렬 처리로 속도 향상 |
| 2-4 | 데이터 생성 실행 (백그라운드) | 4h+ | 천만 건 생성에 수 시간 소요. 병렬 작업 가능 |

### 3단계: 백엔드 API (2일)

| 순번 | 작업 | 예상 시간 | 근거 |
|:----:|------|:--------:|------|
| 3-1 | FastAPI 프로젝트 구조 세팅 (`backend/app/`) | 2h | 표준 디렉토리 구조 및 의존성 설정 |
| 3-2 | 모델/라우터/서비스 기본 구현 (CRUD) | 4h | shipments, companies, warehouses 기본 API |
| 3-3 | 상태 변경 API 구현 (`POST /shipments/{id}/status`) | 4h | Q3 3가지 전략의 분기점. 전략 선택 파라미터 포함 |
| 3-4 | 타임라인 조회 API 구현 (`GET /shipments/{id}/timeline`) | 4h | Q4 2가지 방안의 분기점. 저장소 선택 가능 |

### 4단계: Q3 정합성 전략 구현 (4일)

| 순번 | 작업 | 예상 시간 | 근거 |
|:----:|------|:--------:|------|
| 4-1 | **전략 1: 동기 트랜잭션** (`strategy_1_sync_tx.py`) | 1일 | 가장 단순. 베이스라인 성능 측정용 |
| 4-2 | **전략 2: PostgreSQL 트리거** (`strategy_2_trigger.sql`) | 1일 | DB 레벨 자동화. 트리거 로직 및 테스트 |
| 4-3 | **전략 3: Kafka 비동기** (`strategy_3_kafka.py`, `consumer.py`) | 2일 | 가장 복잡. Producer/Consumer 분리 구현 |

### 5단계: Q4 저장소 비교 (2일)

| 순번 | 작업 | 예상 시간 | 근거 |
|:----:|------|:--------:|------|
| 5-1 | **방안 1: 파티션 쿼리 최적화** (`option_1_partitioning.py`) | 1일 | RDB 내 해결. 파티션 프루닝 효과 검증 |
| 5-2 | **방안 2: ES 동기화 + 조회** (`option_2_elasticsearch.py`) | 1일 | Kafka → ES 파이프라인 + 조회 성능 테스트 |

### 6단계: 벤치마크 및 문서화 (2일)

| 순번 | 작업 | 예상 시간 | 근거 |
|:----:|------|:--------:|------|
| 6-1 | Q3 벤치마크 실행 및 결과 정리 | 1일 | TPS, Latency(p50, p99), 정합성 오류율 비교 |
| 6-2 | Q4 벤치마크 실행 및 결과 정리 | 4h | 조회 응답 시간, CPU/메모리 사용률 비교 |
| 6-3 | 최종 보고서 작성 (README 업데이트) | 4h | 실험 결과 및 결론 정리 |

---

## 📊 프로젝트 개요

| 항목 | 값 |
|------|-----|
| **데이터 규모** | 1,000만 건 (shipments) + 1억 건 (shipment_updates) |
| **핵심 목표** | README 5가지 문제에 대한 실습 기반 검증 |

---

## 🏗️ 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph Client["클라이언트"]
        WEB[웹 대시보드]
    end
    
    subgraph Backend["백엔드 API"]
        API[FastAPI]
    end
    
    subgraph Strategy["Q3: 3가지 정합성 전략"]
        S1[1. 동기 트랜잭션]
        S2[2. DB 트리거]
        S3[3. Kafka 비동기]
    end
    
    subgraph MessageQueue["메시지 브로커"]
        KAFKA[Apache Kafka]
        REDIS[(Redis)]
    end
    
    subgraph Database["Q4: 데이터 저장소"]
        subgraph Option1["방안1: 파티셔닝"]
            PG_PART[(PostgreSQL<br/>파티션 테이블)]
        end
        subgraph Option2["방안2: NoSQL"]
            ES[(Elasticsearch)]
        end
    end
    
    subgraph Archive["Q5: ILM"]
        S3[(S3 Glacier)]
    end
    
    WEB --> API
    API --> S1 & S2 & S3
    S1 --> PG_PART
    S2 --> PG_PART
    S3 --> KAFKA
    KAFKA --> PG_PART
    KAFKA --> ES
    PG_PART --> S3
```

---

## 📁 최종 디렉토리 구조

```
B3_LogisFlow/
├── README.md
│
├── backend/                          # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/
│   │   ├── routers/
│   │   ├── services/
│   │   └── consumers/               # Kafka Consumer
│   │       └── status_sync_consumer.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── schema/                           # DB 스키마 (기존)
│   ├── 01_schema_ddl.sql
│   ├── 02_partitioned_schema.sql    # [신규] 파티션 스키마
│   └── ...
│
├── data_generator/                   # [신규] 천만건 생성기
│   ├── generate_10m.py
│   └── config.yaml
│
├── benchmarks/                       # 벤치마크 & 테스트
│   ├── q3_consistency/              # Q3: 3가지 전략 비교
│   │   ├── strategy_1_sync_tx.py
│   │   ├── strategy_2_trigger.py
│   │   └── strategy_3_kafka.py
│   ├── q4_storage/                  # Q4: 저장소 비교
│   │   ├── option_1_partitioning.py
│   │   └── option_2_elasticsearch.py
│   └── performance/
│       ├── benchmark_v1.py          # 기존
│       └── benchmark_v2.py          # 기존
│
├── scripts/
│   └── archiver.py                  # Q5: ILM 스크립트
│
├── docker-compose.yml               # 전체 환경 구성
└── 참고자료.md
```

---

## 🔬 Q3: 쓰기 정합성 3가지 전략 상세 설계

> README 3번 문제: 비정규화 컬럼의 일관성 유지 방법

### 전략 1: 동기적 애플리케이션 트랜잭션

```mermaid
sequenceDiagram
    participant App
    participant DB
    
    App->>DB: BEGIN TRANSACTION
    App->>DB: INSERT INTO shipment_updates
    App->>DB: UPDATE shipments SET current_status=...
    App->>DB: COMMIT
    Note right of DB: 즉시 일관성 보장<br/>but Lock 경합 발생
```

```python
# strategy_1_sync_tx.py
def update_status_sync(shipment_id: int, new_status: str):
    with db.begin():  # 트랜잭션 시작
        db.execute("""
            INSERT INTO shipment_updates (shipment_id, status_code, timestamp)
            VALUES (%s, %s, NOW())
        """, (shipment_id, new_status))
        
        db.execute("""
            UPDATE shipments 
            SET current_status = %s, last_updated_at = NOW()
            WHERE shipment_id = %s
        """, (new_status, shipment_id))
    # 트랜잭션 커밋 - 둘 다 성공하거나 둘 다 실패
```

| 장점 | 단점 |
|------|------|
| 완벽한 즉시 일관성 | Lock 점유 시간 증가 |
| 구현 단순 | 동시 처리량 감소 |
| 롤백 자동 처리 | Peak 시 병목 |

---

### 전략 2: 데이터베이스 트리거

```mermaid
sequenceDiagram
    participant App
    participant DB
    participant Trigger
    
    App->>DB: INSERT INTO shipment_updates
    DB->>Trigger: AFTER INSERT 이벤트
    Trigger->>DB: UPDATE shipments
    DB-->>App: INSERT 완료
    Note right of Trigger: DB 레벨 자동화<br/>but 숨겨진 로직
```

```sql
-- strategy_2_trigger.sql
CREATE OR REPLACE FUNCTION sync_current_status()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE shipments 
    SET current_status = NEW.status_code,
        last_updated_at = NEW.timestamp
    WHERE shipment_id = NEW.shipment_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_status
AFTER INSERT ON shipment_updates
FOR EACH ROW
EXECUTE FUNCTION sync_current_status();
```

| 장점 | 단점 |
|------|------|
| 앱 코드 수정 불필요 | DB에 숨겨진 로직 |
| 누락 불가능 | 대량 INSERT 시 부하 |
| 트랜잭션 내 실행 | 디버깅 어려움 |

---

### 전략 3: Kafka 비동기 처리 (Eventual Consistency)

```mermaid
sequenceDiagram
    participant App
    participant DB
    participant Kafka
    participant Consumer
    
    App->>DB: INSERT INTO shipment_updates
    App->>Kafka: produce(status_changed)
    App-->>User: 202 Accepted (즉시 응답)
    
    Note over Kafka,Consumer: 비동기 처리
    
    Kafka->>Consumer: consume(status_changed)
    Consumer->>DB: UPDATE shipments
    
    Note right of Consumer: 최종 일관성<br/>수초 지연 가능
```

```python
# strategy_3_kafka.py - Producer
from confluent_kafka import Producer

producer = Producer({'bootstrap.servers': 'localhost:9092'})

def update_status_async(shipment_id: int, new_status: str):
    # 1. 즉시 로그 저장
    db.execute("""
        INSERT INTO shipment_updates (shipment_id, status_code, timestamp)
        VALUES (%s, %s, NOW())
    """, (shipment_id, new_status))
    
    # 2. Kafka로 이벤트 발행
    event = {
        "shipment_id": shipment_id,
        "status": new_status,
        "timestamp": datetime.now().isoformat()
    }
    producer.produce('shipment-status-updates', json.dumps(event))
    producer.flush()
    
    return {"message": "accepted", "status": 202}
```

```python
# status_sync_consumer.py - Consumer
from confluent_kafka import Consumer

consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'status-sync-group',
    'auto.offset.reset': 'earliest'
})
consumer.subscribe(['shipment-status-updates'])

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    
    event = json.loads(msg.value())
    
    # 비정규화 컬럼 동기화
    db.execute("""
        UPDATE shipments 
        SET current_status = %s, last_updated_at = %s
        WHERE shipment_id = %s
    """, (event['status'], event['timestamp'], event['shipment_id']))
```

| 장점 | 단점 |
|------|------|
| 최고의 응답 속도 | 일시적 불일치 |
| 수평 확장 용이 | 인프라 복잡도 증가 |
| 부하 분산 | 메시지 유실 대비 필요 |

---

## 🗄️ Q4: 이력 조회 최적화 2가지 방안 상세

> README 4번 문제: shipment_updates 타임라인 조회 최적화

### 방안 1: PostgreSQL 테이블 파티셔닝

**개념**: 500억 건 테이블을 물리적으로 분리하여 스캔 범위 축소

```mermaid
graph LR
    subgraph "shipment_updates (파티션 테이블)"
        P1[2024_01<br/>1억건]
        P2[2024_02<br/>1억건]
        P3[...<br/>...]
        P4[2025_12<br/>5천만건]
    end
    
    Q[조회: 2025-12-01 ~ 2025-12-31] --> P4
    
    style P4 fill:#90EE90
```

```sql
-- 02_partitioned_schema.sql
CREATE TABLE shipment_updates (
    update_id BIGSERIAL,
    shipment_id INT NOT NULL,
    status_code VARCHAR(50) NOT NULL,
    notes VARCHAR(255),
    timestamp TIMESTAMP NOT NULL,
    PRIMARY KEY (update_id, timestamp)
) PARTITION BY RANGE (timestamp);

-- 월별 자동 파티션 생성
CREATE TABLE shipment_updates_2024_01 
    PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
    
CREATE TABLE shipment_updates_2024_02 
    PARTITION OF shipment_updates
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- ... 24개월분 생성

-- 파티션별 인덱스
CREATE INDEX idx_updates_2024_01_shipment 
    ON shipment_updates_2024_01(shipment_id, timestamp DESC);
```

| 장점 | 단점 |
|------|------|
| 기존 RDB 유지 | 단일 서버 리소스 한계 |
| SQL 호환성 100% | 파티션 관리 필요 |
| 오래된 파티션 쉽게 삭제 | 샤딩 불가 |
| 관리 비용 저렴 | 수십억건 넘으면 한계 |

**적합한 경우**: 데이터가 시간 기반으로 조회되고, 단일 PostgreSQL로 감당 가능할 때

---

### 방안 2: Elasticsearch 이관

**개념**: 이력 데이터를 검색 최적화된 NoSQL로 분리

```mermaid
graph TB
    subgraph "Write Path"
        A[상태 변경] --> B[PostgreSQL<br/>shipment_updates]
        B --> C[Kafka]
        C --> D[Elasticsearch<br/>Indexer]
    end
    
    subgraph "Read Path"
        E[타임라인 조회] --> F{라우팅}
        F -->|최근 7일| B
        F -->|7일+ 이전| G[Elasticsearch]
    end
```

```json
// Elasticsearch 인덱스 설정
PUT /shipment-updates
{
  "settings": {
    "number_of_shards": 5,
    "number_of_replicas": 1
  },
  "mappings": {
    "properties": {
      "shipment_id": { "type": "integer" },
      "status_code": { "type": "keyword" },
      "notes": { "type": "text" },
      "timestamp": { "type": "date" },
      "company_id": { "type": "integer" }
    }
  }
}
```

```python
# option_2_elasticsearch.py
from elasticsearch import Elasticsearch

es = Elasticsearch(['localhost:9200'])

def get_timeline(shipment_id: int):
    result = es.search(
        index="shipment-updates",
        body={
            "query": {"term": {"shipment_id": shipment_id}},
            "sort": [{"timestamp": "desc"}],
            "size": 100
        }
    )
    return [hit['_source'] for hit in result['hits']['hits']]
```

| 장점 | 단점 |
|------|------|
| O(1) 조회 속도 | 이중 저장 비용 |
| 수평 확장 무제한 | 동기화 파이프라인 필요 |
| 풀텍스트 검색 가능 | 운영 복잡도 증가 |
| RDB 부하 분리 | Eventual Consistency |

**적합한 경우**: 조회 패턴이 다양하고(키워드 검색 등), 수십억건 이상일 때

---

### 방안 1 vs 방안 2 선택 가이드

```mermaid
graph TD
    A[조회 최적화 필요] --> B{데이터 규모?}
    B -->|10억건 미만| C{조회 패턴?}
    B -->|10억건 이상| D[방안2: Elasticsearch]
    
    C -->|시간 기반만| E[방안1: 파티셔닝]
    C -->|복합 검색| D
    
    E --> F[단일 PostgreSQL]
    D --> G[PostgreSQL + ES]
```

---

## 📈 데이터 생성 계획 (천만 건)

```yaml
# data_generator/config.yaml
target:
  shipments: 10,000,000       # 천만 건
  updates_per_shipment: 10    # 화물당 평균 10개 상태 변경
  total_updates: 100,000,000  # 1억 건

distribution:
  companies: 10,000
  warehouses: 50,000
  products: 1,000,000
  
timeline:
  start_date: "2023-01-01"
  end_date: "2025-12-31"
```

```python
# generate_10m.py (개선된 버전)
import concurrent.futures
from faker import Faker

def generate_batch(batch_id, batch_size=100000):
    """10만 건씩 병렬 생성"""
    # ... 기존 generator 로직 활용
    
if __name__ == "__main__":
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(generate_batch, i) for i in range(100)]
        # 100 batches x 100,000 = 10,000,000 shipments
```

---

## 🐳 Docker Compose 구성

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: logisflow
      POSTGRES_PASSWORD: logisflow
    volumes:
      - ./schema:/docker-entrypoint-initdb.d
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.4.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - esdata:/usr/share/elasticsearch/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  api:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - kafka
      - elasticsearch
    environment:
      DATABASE_URL: postgresql://postgres:logisflow@postgres:5432/logisflow
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      ELASTICSEARCH_URL: http://elasticsearch:9200

volumes:
  pgdata:
  esdata:
```

---

## 🧪 벤치마크 실행 계획

### Q3 정합성 테스트

```bash
# 3가지 전략 순차 실행
cd benchmarks/q3_consistency

# 전략 1: 동기 트랜잭션
python strategy_1_sync_tx.py --iterations 10000

# 전략 2: DB 트리거
python strategy_2_trigger.py --iterations 10000

# 전략 3: Kafka 비동기
python strategy_3_kafka.py --iterations 10000 --measure-lag
```

**측정 지표**:
- 처리량 (TPS)
- 응답 시간 (p50, p99)
- 정합성 오류율
- 최종 일관성 지연 시간 (Kafka만)

### Q4 저장소 비교

```bash
cd benchmarks/q4_storage

# 방안 1: 파티셔닝
python option_1_partitioning.py --query-count 1000

# 방안 2: Elasticsearch  
python option_2_elasticsearch.py --query-count 1000
```

**측정 지표**:
- 타임라인 조회 시간
- CPU/메모리 사용률
- 인덱스 크기

---

## ✅ 구현 순서

| 순서 | 작업 | 예상 시간 |
|:----:|------|:--------:|
| 1 | Docker Compose 환경 구축 | 1일 |
| 2 | 천만 건 데이터 생성기 | 1일 |
| 3 | FastAPI 기본 API | 2일 |
| 4 | Q3 전략 1 (동기 트랜잭션) | 1일 |
| 5 | Q3 전략 2 (DB 트리거) | 1일 |
| 6 | Q3 전략 3 (Kafka) | 2일 |
| 7 | Q4 방안 1 (파티셔닝) | 2일 |
| 8 | Q4 방안 2 (Elasticsearch) | 2일 |
| 9 | 벤치마크 & 결과 정리 | 2일 |
