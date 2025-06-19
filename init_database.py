#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
새로운 스키마로 데이터베이스를 생성합니다.
"""

import sqlite3
import os

def init_database():
    """데이터베이스 초기화"""
    db_path = "Callytics.sqlite"
    
    # 기존 데이터베이스 백업
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup"
        print(f"기존 데이터베이스를 {backup_path}로 백업합니다...")
        os.rename(db_path, backup_path)
    
    print("새로운 데이터베이스를 생성합니다...")
    
    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # EnhancedSchema.sql 읽기
    with open("src/db/sql/EnhancedSchema.sql", "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    # 스키마 실행
    try:
        cursor.executescript(schema_sql)
        conn.commit()
        print("✅ 데이터베이스 스키마 생성 완료!")
        
        # 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"생성된 테이블: {[table[0] for table in tables]}")
        
    except Exception as e:
        print(f"❌ 스키마 생성 실패: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_database() 