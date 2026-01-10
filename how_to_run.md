### 실행방법 상세 설명서.

#### 1-1 진행하면서 테스트
`.env.example` 파일 바탕으로 .env 파일 생성.
```
도커 실행 
# 2. Docker Compose 실행 (백그라운드 모드)
docker-compose up -d

# 3. 컨테이너 상태 확인
docker-compose ps

# 4. 서비스별 헬스체크 확인 (healthy 상태가 되어야 정상)
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

```
```
# 정상 구동 확인 방법
# PostgreSQL 접속 테스트
docker exec -it logisflow-postgres psql -U postgres -d logisflow -c "SELECT 1;"

# postgresql 테이블 생성여부 확인 
docker exec -it logisflow-postgres psql -U postgres -d logisflow -c "\dt"

# Kafka 연결 테스트
docker exec -it logisflow-kafka kafka-topics --bootstrap-server localhost:9092 --list

# Elasticsearch 상태 확인
curl http://localhost:9200/_cluster/health?pretty

# 또는 브라우저에서 http://localhost:9200 접속
# Redis 테스트
docker exec -it logisflow-redis redis-cli ping
```


#### 1-2 스키마 생성 후 새로운 서버로 도커와 pgadmin4 연결
Step 1: 새 서버 등록
pgAdmin 4 왼쪽 패널에서 Servers 우클릭
Register → Server... 클릭

Step 2: General 탭

| 항목 | 값 |
| :--- | :--- |
| Name | `LogisFlow Docker` (원하는 이름) |

Step 3: Connection 탭 

> 실행해보고 에러날시 로컬 포트랑 겹칠 가능성 존재.
방법 1. 로컬 postgresql 중지
방법 2. 도커 포트 변경. (DH 추천) - 이 프젝에서 적용(DH)
- docker-compose.yml 파일 59번째 줄 "5432:5432" => 5433:5432로 변경
- 이후 아래 표에서 PORT 5432 -> 5433으로 변경 후 생성.

| 항목 | 값 |
| :--- | :--- |
| **Host name/address** | `localhost` |
| **Port** | `5432` or `5433`으로 변경|
| **Maintenance database** | `logisflow` |
| **Username** | `postgres` |
| **Password** | `logisflow1234` |
| ✅ **Save password** | 체크 |

step 4 : .env파일 database부분
> DATABASE_URL=postgresql://postgres:logisflow1234@localhost:5433/logisflow
이걸로 변경(포트번호만 change)