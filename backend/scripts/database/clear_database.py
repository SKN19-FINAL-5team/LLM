#!/usr/bin/env python3
"""
데이터베이스 정리 스크립트
기존 documents와 chunks 테이블을 비워서 새로 시작할 수 있게 합니다.

사용법:
  python backend/scripts/clear_database.py --force
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def main():
    print("=" * 80)
    print("⚠️  데이터베이스 정리")
    print("=" * 80)
    print("\n이 스크립트는 다음 테이블의 모든 데이터를 삭제합니다:")
    print("  - documents 테이블")
    print("  - chunks 테이블")
    print("\n⚠️  주의: 이 작업은 되돌릴 수 없습니다!")
    
    # --force 플래그 확인
    if '--force' not in sys.argv:
        print("\n❌ 이 스크립트를 실행하려면 --force 플래그를 사용하세요:")
        print("   python backend/scripts/database/clear_database.py --force")
        return
    
    # 데이터베이스 연결
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        cur = conn.cursor()
        print("\n✅ 데이터베이스 연결 성공")
    except Exception as e:
        print(f"\n❌ 데이터베이스 연결 실패: {e}")
        return
    
    # 현재 데이터 확인
    print("\n📊 현재 데이터 상태:")
    cur.execute("SELECT COUNT(*) FROM documents")
    doc_count = cur.fetchone()[0]
    print(f"  - 문서 수: {doc_count:,}개")
    
    cur.execute("SELECT COUNT(*) FROM chunks")
    chunk_count = cur.fetchone()[0]
    print(f"  - 청크 수: {chunk_count:,}개")
    
    cur.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL")
    embedded_count = cur.fetchone()[0]
    print(f"  - 임베딩된 청크: {embedded_count:,}개")
    
    # 테이블 비우기
    print("\n🗑️  테이블 비우는 중...")
    try:
        # chunks를 먼저 비우고 (외래키 제약 때문)
        cur.execute("TRUNCATE TABLE chunks CASCADE;")
        print("  ✅ chunks 테이블 비움")
        
        # documents 비우기
        cur.execute("TRUNCATE TABLE documents CASCADE;")
        print("  ✅ documents 테이블 비움")
        
        conn.commit()
        print("\n✅ 데이터베이스 정리 완료!")
        print("\n이제 다음 명령어로 임베딩을 새로 시작할 수 있습니다:")
        print("  conda run -n ddoksori python backend/scripts/embedding/embed_data_remote.py")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 오류 발생: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
