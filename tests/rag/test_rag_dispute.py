#!/usr/bin/env python3
"""
분쟁조정 사례 데이터 RAG 테스트 스크립트

분쟁조정 사례 데이터(doc_type='mediation_case')만 검색하는 RAG 테스트
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트와 backend 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

from app.rag import VectorRetriever

# 환경 변수 로드
load_dotenv()


def test_dispute_rag():
    """분쟁조정 사례 데이터 RAG 테스트"""
    print("=" * 80)
    print("⚖️  분쟁조정 사례 데이터 RAG 테스트")
    print("=" * 80)
    
    # 검색 전략 설명
    print("\n[검색 전략]")
    print("  Vector Similarity Search with doc_type='mediation_case' filter")
    print("  - 코사인 유사도 기반 벡터 검색")
    print("  - 분쟁조정 사례 데이터만 검색 (doc_type='mediation_case')")
    
    # DB 설정
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # Retriever 초기화
    retriever = VectorRetriever(db_config)
    
    # 필터 조건 출력
    print("\n[필터 조건]")
    print("  - doc_type: 'mediation_case'")
    print("  - chunk_types: None (모든 청크 타입)")
    print("  - agencies: None (모든 기관)")
    
    # 테스트 쿼리
    test_queries = [
        "온라인 쇼핑몰 환불 거부 사례는?",
        "에어컨 설치 불량으로 인한 누수 배상 사례는?",
        "휴대폰 액정 자연 파손 수리 사례는?",
    ]
    
    for idx, query in enumerate(test_queries, 1):
        print("\n" + "-" * 80)
        print(f"[테스트 쿼리 {idx}]")
        print(f"질문: {query}")
        print("-" * 80)
        
        try:
            # 검색 실행
            chunks = retriever.search(query=query, top_k=10)
            
            # doc_type='mediation_case' 필터링
            dispute_chunks = [
                chunk for chunk in chunks 
                if chunk.get('source') == 'mediation_case'
            ]
            
            print(f"\n검색 결과: {len(dispute_chunks)}개의 분쟁조정 사례 청크 발견 (전체 {len(chunks)}개 중)")
            
            if not dispute_chunks:
                print("⚠️  분쟁조정 사례 데이터가 검색되지 않았습니다.")
                print("   데이터베이스에 분쟁조정 사례 데이터가 임베딩되어 있는지 확인하세요.")
                continue
            
            # 상위 5개만 출력
            for i, chunk in enumerate(dispute_chunks[:5], 1):
                print(f"\n[결과 {i}]")
                print(f"  유사도: {chunk.get('similarity', 0):.4f}")
                print(f"  청크 타입: {chunk.get('chunk_type', 'N/A')}")
                print(f"  기관: {chunk.get('agency', 'N/A')}")
                print(f"  사건번호: {chunk.get('case_no', 'N/A')}")
                print(f"  결정일자: {chunk.get('decision_date', 'N/A')}")
                print(f"  문서 ID: {chunk.get('case_uid', 'N/A')}")
                content = chunk.get('text', '') or chunk.get('content', '')
                content_preview = content[:150] + "..." if len(content) > 150 else content
                print(f"  내용 미리보기: {content_preview}")
            
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
    
    retriever.close()
    print("\n" + "=" * 80)
    print("✅ 분쟁조정 사례 데이터 RAG 테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    test_dispute_rag()
