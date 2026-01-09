#!/usr/bin/env python3
"""
기존 DB 문서에 키워드 메타데이터 추가 스크립트

Usage:
    cd /home/maroco/ddoksori_demo/backend/scripts
    conda run -n ddoksori python update_metadata_keywords.py
"""

import sys
from pathlib import Path
import psycopg2
import os
import json
from dotenv import load_dotenv
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.data_processing.metadata_enricher import MetadataEnricher

# .env 로드
load_dotenv(project_root / '.env')


def update_metadata():
    """기존 문서의 메타데이터 업데이트"""
    print("=" * 80)
    print("메타데이터 키워드 추출 시작")
    print("=" * 80)
    
    # DB 연결
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        cur = conn.cursor()
        print("✅ DB 연결 성공")
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return
    
    # MetadataEnricher 초기화
    enricher = MetadataEnricher()
    print("✅ MetadataEnricher 초기화 완료")
    
    # 모든 문서 가져오기
    print("\n문서 목록 가져오는 중...")
    cur.execute("""
        SELECT d.doc_id, string_agg(c.content, ' ' ORDER BY c.chunk_index) as full_content
        FROM documents d
        JOIN chunks c ON d.doc_id = c.doc_id
        WHERE c.drop = FALSE
        GROUP BY d.doc_id
    """)
    
    docs = cur.fetchall()
    total_docs = len(docs)
    print(f"✅ {total_docs}개 문서 발견")
    
    # 진행 상황 추적
    updated_count = 0
    error_count = 0
    start_time = datetime.now()
    
    print("\n메타데이터 추출 및 업데이트 시작...")
    print(f"{'문서 ID':<50} {'상태':<10} {'키워드 수':<10} {'진행률':<10}")
    print("-" * 80)
    
    for idx, (doc_id, full_content) in enumerate(docs, 1):
        progress = (idx / total_docs) * 100
        
        try:
            # 키워드 추출
            keywords = enricher.extract_keywords(full_content, top_k=15)
            
            # 엔티티 추출
            entities = enricher.extract_entities(full_content)
            
            # 법률 용어 추출
            legal_terms = enricher.extract_legal_terms(full_content)
            
            # 카테고리 추론 (단일 카테고리 반환)
            category = enricher.infer_category(full_content)
            
            # 메타데이터 업데이트 준비
            metadata_update = {
                'keywords': keywords,
                'products': entities.get('products', [])[:10],
                'companies': entities.get('companies', [])[:5],
                'legal_terms': legal_terms[:20]
            }
            
            if category:
                metadata_update['category'] = category
            
            # DB 업데이트 (기존 메타데이터와 병합)
            cur.execute("""
                UPDATE documents
                SET metadata = metadata || %s::jsonb,
                    updated_at = NOW()
                WHERE doc_id = %s
            """, (json.dumps(metadata_update), doc_id))
            
            updated_count += 1
            
            # 진행 상황 출력
            status = "✅"
            doc_id_short = doc_id[:47] + "..." if len(doc_id) > 50 else doc_id
            print(f"{doc_id_short:<50} {status:<10} {len(keywords):<10} {progress:>6.1f}%")
            
            # 주기적으로 커밋
            if idx % 100 == 0:
                conn.commit()
                elapsed = (datetime.now() - start_time).total_seconds()
                avg_time = elapsed / idx
                remaining = (total_docs - idx) * avg_time
                print(f"  💾 중간 커밋 완료 ({idx}/{total_docs}) - 예상 남은 시간: {remaining/60:.1f}분")
        
        except Exception as e:
            error_count += 1
            status = "❌"
            doc_id_short = doc_id[:47] + "..." if len(doc_id) > 50 else doc_id
            print(f"{doc_id_short:<50} {status:<10} {'오류':<10} {progress:>6.1f}%")
            print(f"  오류 내용: {str(e)}")
    
    # 최종 커밋
    conn.commit()
    
    # 결과 요약
    elapsed_time = (datetime.now() - start_time).total_seconds()
    
    print("\n" + "=" * 80)
    print("메타데이터 업데이트 완료")
    print("=" * 80)
    print(f"  - 총 문서: {total_docs}개")
    print(f"  - 업데이트 성공: {updated_count}개")
    print(f"  - 오류: {error_count}개")
    print(f"  - 소요 시간: {elapsed_time/60:.1f}분")
    print(f"  - 평균 처리 시간: {elapsed_time/total_docs:.2f}초/문서")
    
    # 검증 쿼리
    print("\n메타데이터 커버리지 확인:")
    cur.execute("""
        SELECT 
            doc_type,
            COUNT(*) as total_docs,
            COUNT(CASE WHEN metadata ? 'keywords' THEN 1 END) as has_keywords,
            ROUND(100.0 * COUNT(CASE WHEN metadata ? 'keywords' THEN 1 END) / COUNT(*), 2) as coverage_pct
        FROM documents
        GROUP BY doc_type
        ORDER BY doc_type
    """)
    
    print(f"{'문서 타입':<30} {'총 문서':<10} {'키워드 있음':<15} {'커버리지':<10}")
    print("-" * 80)
    for row in cur.fetchall():
        doc_type, total, has_kw, coverage = row
        print(f"{doc_type:<30} {total:<10} {has_kw:<15} {coverage:>6.1f}%")
    
    # 정리
    cur.close()
    conn.close()
    
    print("\n✅ 메타데이터 키워드 추출 완료!")


if __name__ == "__main__":
    update_metadata()
