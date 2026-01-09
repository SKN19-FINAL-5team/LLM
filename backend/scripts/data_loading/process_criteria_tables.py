#!/usr/bin/env python3
"""
table 1/3/4 기준 데이터를 DB에 삽입하는 스크립트

Usage:
    cd /home/maroco/ddoksori_demo/backend/scripts
    conda run -n ddoksori python process_criteria_tables.py
"""

import sys
from pathlib import Path
import psycopg2
import os
from dotenv import load_dotenv

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.data_processing.data_transform_pipeline import DataTransformer
from scripts.data_processing.db_inserter import insert_documents_to_db

# .env 로드
load_dotenv(project_root / '.env')


def main():
    """메인 함수"""
    print("=" * 80)
    print("기준 데이터 (table 1/3/4) 일괄 처리 시작")
    print("=" * 80)
    
    # 데이터 디렉토리
    criteria_dir = project_root / "data" / "criteria"
    
    if not criteria_dir.exists():
        print(f"❌ 기준 데이터 디렉토리를 찾을 수 없습니다: {criteria_dir}")
        return
    
    # 처리할 테이블 정의
    tables = [
        {
            'file': 'table1_item_chunks.jsonl',
            'transform_func': 'transform_criteria_table1',
            'description': '품목 분류'
        },
        {
            'file': 'table3_warranty_chunks.jsonl',
            'transform_func': 'transform_criteria_table3',
            'description': '품질보증기간'
        },
        {
            'file': 'table4_lifespan_chunks.jsonl',
            'transform_func': 'transform_criteria_table4',
            'description': '내구연한'
        }
    ]
    
    # 파일 존재 확인
    print("\n파일 존재 확인:")
    for table in tables:
        file_path = criteria_dir / table['file']
        exists = "✅" if file_path.exists() else "❌"
        print(f"  {exists} {table['file']}")
        table['file_path'] = file_path
    
    # DB 연결
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        print("\n✅ DB 연결 성공")
    except Exception as e:
        print(f"\n❌ DB 연결 실패: {e}")
        return
    
    # 데이터 변환기 초기화
    transformer = DataTransformer(use_db=False, enrich_metadata=False)
    
    total_docs = 0
    total_chunks = 0
    errors = []
    
    # 각 테이블 처리
    for table in tables:
        if not table['file_path'].exists():
            error_msg = f"{table['file']}: 파일을 찾을 수 없음"
            errors.append(error_msg)
            print(f"\n❌ {error_msg}")
            continue
        
        print(f"\n{'=' * 80}")
        print(f"처리 중: {table['description']} ({table['file']})")
        print(f"{'=' * 80}")
        
        try:
            # 변환 함수 호출
            transform_func = getattr(transformer, table['transform_func'])
            result = transform_func(str(table['file_path']))
            
            # DB 삽입
            docs_inserted, chunks_inserted = insert_documents_to_db(result['documents'], conn)
            
            total_docs += docs_inserted
            total_chunks += chunks_inserted
            
            print(f"  ✅ 완료: {docs_inserted}개 문서, {chunks_inserted}개 청크")
        
        except Exception as e:
            error_msg = f"{table['file']}: {str(e)}"
            errors.append(error_msg)
            print(f"  ❌ 오류: {e}")
            import traceback
            traceback.print_exc()
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("처리 완료")
    print("=" * 80)
    print(f"  - 처리된 테이블: {len(tables)}개")
    print(f"  - 삽입된 문서: {total_docs}개")
    print(f"  - 삽입된 청크: {total_chunks}개")
    print(f"  - 오류: {len(errors)}개")
    
    if errors:
        print("\n오류 목록:")
        for error in errors:
            print(f"  - {error}")
    
    # 정리
    transformer.close()
    conn.close()
    
    print("\n✅ 기준 데이터 처리 완료!")


if __name__ == "__main__":
    main()
