#!/usr/bin/env python3
"""
13개 법령 데이터를 DB에 삽입하는 스크립트

Usage:
    cd /home/maroco/ddoksori_demo/backend/scripts
    conda run -n ddoksori python process_all_laws.py
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
    print("법령 데이터 일괄 처리 시작")
    print("=" * 80)
    
    # 데이터 디렉토리
    law_dir = project_root / "data" / "law"
    
    if not law_dir.exists():
        print(f"❌ 법령 데이터 디렉토리를 찾을 수 없습니다: {law_dir}")
        return
    
    # 법령 파일 목록 (중복 제거)
    law_files = []
    seen_files = set()
    
    for law_file in sorted(law_dir.glob("*.jsonl")):
        # E-Commerce vs E_Commerce 중복 제거 (언더스코어 버전 우선)
        base_name = law_file.stem.replace('-', '_')
        
        if base_name in seen_files:
            print(f"  ⚠️  중복 파일 스킵: {law_file.name}")
            continue
        
        seen_files.add(base_name)
        law_files.append(law_file)
    
    print(f"\n발견된 법령 파일: {len(law_files)}개")
    for f in law_files:
        print(f"  - {f.name}")
    
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
    
    # 각 법령 파일 처리
    for law_file in law_files:
        print(f"\n{'=' * 80}")
        print(f"처리 중: {law_file.name}")
        print(f"{'=' * 80}")
        
        try:
            # 변환
            result = transformer.transform_law_single_file(str(law_file))
            
            # DB 삽입
            docs_inserted, chunks_inserted = insert_documents_to_db(result['documents'], conn)
            
            total_docs += docs_inserted
            total_chunks += chunks_inserted
            
            print(f"  ✅ 완료: {docs_inserted}개 문서, {chunks_inserted}개 청크")
        
        except Exception as e:
            error_msg = f"{law_file.name}: {str(e)}"
            errors.append(error_msg)
            print(f"  ❌ 오류: {e}")
            import traceback
            traceback.print_exc()
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("처리 완료")
    print("=" * 80)
    print(f"  - 처리된 파일: {len(law_files)}개")
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
    
    print("\n✅ 법령 데이터 처리 완료!")


if __name__ == "__main__":
    main()
