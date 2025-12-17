import re

# 입력 및 출력 파일명 설정
input_file = '04_shipment_backup.sql'
output_file = '04_shipment_backup_pg_fixed.sql'

def convert_mysql_to_postgres(sql_content):
    # 1. 백틱(`) 제거
    sql_content = sql_content.replace('`', '')
    
    # 2. 주석 처리된 MySQL 전용 명령어 제거
    sql_content = re.sub(r'/\*!.*?\*/;', '', sql_content, flags=re.DOTALL)
    
    # 3. AUTO_INCREMENT -> SERIAL 변환
    sql_content = re.sub(r'int\s+NOT\s+NULL\s+AUTO_INCREMENT', 'SERIAL', sql_content, flags=re.IGNORECASE)
    
    # 4. MySQL 전용 테이블 옵션 제거
    sql_content = re.sub(r'\)\s*ENGINE=InnoDB.*?;', ');', sql_content, flags=re.IGNORECASE)
    
    # 5. LOCK/UNLOCK 제거
    sql_content = re.sub(r'LOCK TABLES.*?;', '', sql_content, flags=re.IGNORECASE)
    sql_content = re.sub(r'UNLOCK TABLES;', '', sql_content, flags=re.IGNORECASE)
    
    # 6. 인코딩/COLLATE 제거
    sql_content = re.sub(r'\s+COLLATE\s+\w+', '', sql_content, flags=re.IGNORECASE)
    sql_content = re.sub(r'\s+CHARACTER SET\s+\w+', '', sql_content, flags=re.IGNORECASE)
    
    # 7. DROP TABLE 문에 CASCADE 추가 (의존성 오류 해결 핵심!)
    # "DROP TABLE IF EXISTS table_name;" -> "DROP TABLE IF EXISTS table_name CASCADE;"
    sql_content = re.sub(r'DROP TABLE IF EXISTS\s+(\w+);', r'DROP TABLE IF EXISTS \1 CASCADE;', sql_content, flags=re.IGNORECASE)

    # 8. KEY(인덱스) 정의 주석 처리
    lines = sql_content.split('\n')
    pg_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('KEY ') and not stripped.startswith('PRIMARY KEY') and not stripped.startswith('FOREIGN KEY'):
            pg_lines.append('-- ' + line) 
        else:
            pg_lines.append(line)
            
    sql_content = '\n'.join(pg_lines)
    
    # 9. 콤마 정리
    sql_content = re.sub(r',\s*--.*?\n\s*\)', '\n)', sql_content)
    sql_content = re.sub(r',\s*\n\s*\)', '\n)', sql_content)

    # 10. 파일 상단 설정 추가 (인코딩 오류 해결 핵심!)
    # client_encoding을 UTF8로 설정하여 psql이 파일을 올바르게 읽도록 함
    header = "SET client_encoding = 'UTF8';\nSET session_replication_role = 'replica';\n\n"
    footer = "\n\nSET session_replication_role = 'origin';"
    
    return header + sql_content + footer

# 파일 변환 실행
try:
    # utf-8로 읽어서 처리
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    pg_content = convert_mysql_to_postgres(content)
    
    # utf-8로 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(pg_content)
        
    print(f"수정 완료! '{output_file}' 파일이 생성되었습니다.")
    
except FileNotFoundError:
    print(f"'{input_file}' 파일을 찾을 수 없습니다.")