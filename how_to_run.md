###

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

# Kafka 연결 테스트
docker exec -it logisflow-kafka kafka-topics --bootstrap-server localhost:9092 --list

# Elasticsearch 상태 확인
curl http://localhost:9200/_cluster/health?pretty

# 또는 브라우저에서 http://localhost:9200 접속
# Redis 테스트
docker exec -it logisflow-redis redis-cli ping
```