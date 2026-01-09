"""
똑소리 프로젝트 - 유사도 검색 테스트 스크립트
작성일: 2026-01-05

사용법:
  python scripts/test_similarity_search.py
  python scripts/test_similarity_search.py "사용자 질문"
"""

import psycopg2
import requests
import json
from dotenv import load_dotenv
import os
import sys

# 환경변수 로드
load_dotenv()

def get_embedding(text: str, api_url: str) -> list:
    """텍스트를 임베딩 벡터로 변환"""
    try:
        response = requests.post(api_url, json={"text": text}, timeout=10)
        response.raise_for_status()
        return response.json()['embedding']
    except Exception as e:
        print(f"❌ 임베딩 API 오류: {e}")
        sys.exit(1)


def search_similar_chunks(conn, query_embedding: list, top_k: int = 5):
    """유사도 검색 실행"""
    cur = conn.cursor()
    
    # 벡터 유사도 검색
    cur.execute("""
        SELECT 
            c.chunk_id,
            c.doc_id,
            d.doc_type,
            d.title,
            c.chunk_type,
            c.content,
            1 - (c.embedding <=> %s::vector) as similarity
        FROM chunks c
        JOIN documents d ON c.doc_id = d.doc_id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """, (query_embedding, query_embedding, top_k))
    
    results = cur.fetchall()
    cur.close()
    
    return results


def main():
    # 테스트 쿼리
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
    else:
        test_query = "온라인 쇼핑몰에서 구매한 제품이 불량이에요. 환불 받을 수 있나요?"
    
    print("=" * 80)
    print("똑소리 프로젝트 - 유사도 검색 테스트")
    print("=" * 80)
    print(f"\n🔍 테스트 쿼리: {test_query}")
    print("-" * 80)
    
    # 데이터베이스 연결
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)
    
    # 임베딩 API URL
    embed_api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
    
    # 1. 쿼리 임베딩 생성
    print(f"\n📡 임베딩 API 호출 중... ({embed_api_url})")
    query_embedding = get_embedding(test_query, embed_api_url)
    print(f"✅ 쿼리 임베딩 생성 완료 (차원: {len(query_embedding)})")
    
    # 2. 유사도 검색
    print(f"\n🔎 유사도 검색 실행 중...")
    results = search_similar_chunks(conn, query_embedding, top_k=5)
    
    if not results:
        print("❌ 검색 결과가 없습니다. 임베딩이 완료되었는지 확인하세요.")
        conn.close()
        sys.exit(1)
    
    print(f"✅ 상위 {len(results)}개 유사 청크 발견")
    print("\n" + "=" * 80)
    print("검색 결과")
    print("=" * 80)
    
    for i, row in enumerate(results, 1):
        chunk_id, doc_id, doc_type, doc_title, chunk_type, content, similarity = row
        
        print(f"\n[{i}] 유사도: {similarity:.4f} ({similarity*100:.2f}%)")
        print(f"    청크 ID: {chunk_id}")
        print(f"    문서 ID: {doc_id}")
        print(f"    문서 유형: {doc_type}")
        print(f"    문서 제목: {doc_title[:80]}{'...' if len(doc_title) > 80 else ''}")
        print(f"    청크 타입: {chunk_type}")
        print(f"    내용 미리보기:")
        
        # 내용을 200자로 제한하여 출력
        content_preview = content[:200] + "..." if len(content) > 200 else content
        for line in content_preview.split('\n'):
            if line.strip():
                print(f"      {line.strip()}")
    
    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)
    
    # 추가 테스트 쿼리 제안
    print("\n💡 다른 쿼리로 테스트해보세요:")
    print("  python scripts/test_similarity_search.py \"청약철회 기간은 얼마나 되나요?\"")
    print("  python scripts/test_similarity_search.py \"아파트 하자보수는 어떻게 신청하나요?\"")
    print("  python scripts/test_similarity_search.py \"소비자분쟁조정위원회는 무엇인가요?\"")
    
    conn.close()


if __name__ == "__main__":
    main()
