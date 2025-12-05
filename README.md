# database_tradeoff
"Database Design Trade-offs: The Balance Between Normalization and Performance"

## 데이터 파일 확보.
---
> 데이터 스키마 아키텍처 짜기
> 데이터 생성 (범위 정하기)

## 목요일 진행

이후 데이터 베이스 정규화 / 비정규화 진행 후 각각 성능 비교

mysql -u root -ptest1234 -e "DROP DATABASE IF EXISTS shipment; CREATE DATABASE shipment;"

mysql -u root -ptest1234 shipment < schema/01_schema_ddl.sql

mysql -u root -ptest1234 shipment < schema/02_seed_data.sql

mysql -u root -ptest1234 shipment < schema/02_seed_data.sql


## 2025_12_05

