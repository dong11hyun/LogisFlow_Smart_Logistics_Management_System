# database_tradeoff
Database Design Trade-offs: The Balance Between Normalization and Performance

### 데이터 베이스 정규화 / 비정규화 진행 후 각각 성능 비교
```
mysql -u root -p'암호' -e "DROP DATABASE IF EXISTS shipment; CREATE DATABASE shipment;"  필수 실행!
mysql -u root -p'암호' shipment < schema/01_schema_ddl.sql
mysql -u root -p'암호' shipment < schema/02_seed_data.sql
mysql -u root -p'암호' shipment < schema/03_test_data_dump_3000.sql
mysql -u root -p'암호' shipment < schema/04_shipment_backup.sql
```

#### 2025_12_05
04_shipment_backup = > 약 50만건 더미데이터.

- 정규화 테이블 조회 방법 / 인덱스회피 / 성능과부하
``` sql
SELECT SQL_NO_CACHE 
    s.shipment_id,
    s.created_at,
    (SELECT status_code 
     FROM shipment_updates u 
     -- 컬럼에 연산(+0)을 붙이면 인덱스를 못 타고 풀스캔
     WHERE (u.shipment_id + 0) = s.shipment_id 
     ORDER BY timestamp DESC 
     LIMIT 1) AS current_status
FROM 
    shipments s
LIMIT 500;
```
> LIMIT 500500 row(s) returned23.641 sec / 6.375 sec </결과> 

#### 2025_12_06
비정규화 진행
1. 비정규화 컬럼 추가 (현재 상태, 최종 업데이트 시간)
```sql
ALTER TABLE shipments
ADD COLUMN current_status VARCHAR(50) DEFAULT '접수대기',
ADD COLUMN last_updated_at DATETIME;
```
2. 기존 로그 데이터를 바탕으로 최신 상태값 채워넣기 (Update Join)
```sql
UPDATE shipments s
JOIN (
    -- 각 화물별로 가장 최신 로그(timestamp가 제일 큰 것)를 찾는 쿼리
    SELECT t1.shipment_id, t1.status_code, t1.timestamp
    FROM shipment_updates t1
    JOIN (
        SELECT shipment_id, MAX(timestamp) as max_ts
        FROM shipment_updates
        GROUP BY shipment_id
    ) t2 ON t1.shipment_id = t2.shipment_id AND t1.timestamp = t2.max_ts
) latest_log ON s.shipment_id = latest_log.shipment_id
SET 
    s.current_status = latest_log.status_code,
    s.last_updated_at = latest_log.timestamp;
```
3. 비정규화 테이블 조회
```sql
SELECT SQL_NO_CACHE
    s.shipment_id,
    s.created_at,
    s.current_status  -- 핵심(서브쿼리 삭제 -> 컬럼 조회)
FROM 
    shipments s
LIMIT 500;
```

> LIMIT 500	500 row(s) returned	0.000 sec / 0.000 sec </결과>

#### 2025_12_13 정규화/ 인덱스 정규화 / 비정규화 성능 비교 모니터링
``` 
    python benchmark_v1(정규화_비정규화).py 
    python benchmark_v2(인덱스_비정규화).py
    - 위 코드 실행 후 성능체크.
    - 파일 클릭 후 mysql 비밀번호 입력 필요.
    - import 체크 후 필요한 파일 설치 필요.
```

