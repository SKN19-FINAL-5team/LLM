"""
RAG 시스템 테스트 스크립트
Vector DB 검색 및 LLM 답변 생성 기능을 테스트합니다.
"""

import os
import sys
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag import VectorRetriever, RAGGenerator

# 환경 변수 로드
load_dotenv()


def test_retriever():
    """Vector DB 검색 기능 테스트"""
    print("=" * 60)
    print("1. Vector DB 검색 기능 테스트")
    print("=" * 60)
    
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
    
    # 테스트 쿼리
    test_queries = [
        "에어컨 설치 불량으로 누수가 발생했는데 배상받을 수 있나요?",
        "온라인 쇼핑몰에서 환불을 거부당했습니다.",
        "휴대폰 액정이 자연 파손되었는데 무상 수리가 가능한가요?"
    ]
    
    for idx, query in enumerate(test_queries, 1):
        print(f"\n[테스트 쿼리 {idx}]")
        print(f"질문: {query}")
        print("-" * 60)
        
        try:
            # 검색 실행
            chunks = retriever.search(query=query, top_k=3)
            
            print(f"검색 결과: {len(chunks)}개의 청크 발견\n")
            
            for i, chunk in enumerate(chunks, 1):
                print(f"[결과 {i}]")
                print(f"  사건번호: {chunk.get('case_no', 'N/A')}")
                print(f"  기관: {chunk.get('agency', 'N/A')}")
                print(f"  청크 타입: {chunk.get('chunk_type', 'N/A')}")
                print(f"  유사도: {chunk.get('similarity', 0):.4f}")
                print(f"  텍스트 길이: {chunk.get('text_len', 0)}자")
                print(f"  내용 미리보기: {chunk.get('text', '')[:100]}...")
                print()
            
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
    
    retriever.close()
    print("\n✅ Vector DB 검색 테스트 완료\n")


def test_generator():
    """LLM 답변 생성 기능 테스트"""
    print("=" * 60)
    print("2. LLM 답변 생성 기능 테스트")
    print("=" * 60)
    
    # OpenAI API 키 확인
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print("⚠️  OPENAI_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 실제 API 키를 입력해야 이 테스트를 실행할 수 있습니다.")
        print("   검색 기능만 테스트하려면 test_retriever()만 실행하세요.\n")
        return
    
    # DB 설정
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # RAG 컴포넌트 초기화
    retriever = VectorRetriever(db_config)
    generator = RAGGenerator()
    
    # 테스트 쿼리
    query = "에어컨 설치 불량으로 누수가 발생했는데 배상받을 수 있나요?"
    
    print(f"\n[테스트 질문]")
    print(f"{query}")
    print("-" * 60)
    
    try:
        # 1. 검색
        print("\n[1단계] Vector DB에서 관련 사례 검색 중...")
        chunks = retriever.search(query=query, top_k=5)
        print(f"✅ {len(chunks)}개의 관련 청크 발견")
        
        # 2. 답변 생성
        print("\n[2단계] LLM으로 답변 생성 중...")
        result = generator.generate_answer(query=query, chunks=chunks)
        
        # 3. 결과 출력
        print("\n[생성된 답변]")
        print("-" * 60)
        print(result['answer'])
        print("-" * 60)
        
        print(f"\n[메타데이터]")
        print(f"  모델: {result['model']}")
        print(f"  사용된 청크 수: {result['chunks_used']}")
        if 'usage' in result:
            print(f"  토큰 사용량:")
            print(f"    - 프롬프트: {result['usage']['prompt_tokens']}")
            print(f"    - 완성: {result['usage']['completion_tokens']}")
            print(f"    - 총합: {result['usage']['total_tokens']}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
    
    retriever.close()
    print("\n✅ LLM 답변 생성 테스트 완료\n")


def test_full_pipeline():
    """전체 RAG 파이프라인 테스트"""
    print("=" * 60)
    print("3. 전체 RAG 파이프라인 테스트")
    print("=" * 60)
    
    # OpenAI API 키 확인
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print("⚠️  OPENAI_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 실제 API 키를 입력해야 이 테스트를 실행할 수 있습니다.\n")
        return
    
    # DB 설정
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # RAG 컴포넌트 초기화
    retriever = VectorRetriever(db_config)
    generator = RAGGenerator()
    
    # 다양한 테스트 케이스
    test_cases = [
        {
            "query": "휴대폰 액정이 자연 파손되었는데 무상 수리가 가능한가요?",
            "chunk_types": ["decision", "judgment"]
        },
        {
            "query": "온라인 쇼핑몰에서 환불을 거부당했습니다.",
            "agencies": ["kca", "ecmc"]
        }
    ]
    
    for idx, test_case in enumerate(test_cases, 1):
        print(f"\n[테스트 케이스 {idx}]")
        print(f"질문: {test_case['query']}")
        if 'chunk_types' in test_case:
            print(f"청크 타입 필터: {test_case['chunk_types']}")
        if 'agencies' in test_case:
            print(f"기관 필터: {test_case['agencies']}")
        print("-" * 60)
        
        try:
            # 검색
            chunks = retriever.search(
                query=test_case['query'],
                top_k=3,
                chunk_types=test_case.get('chunk_types'),
                agencies=test_case.get('agencies')
            )
            
            # 답변 생성
            result = generator.generate_answer(
                query=test_case['query'],
                chunks=chunks
            )
            
            # 결과 출력
            print(f"\n[답변]")
            print(result['answer'])
            print(f"\n(사용된 청크: {result['chunks_used']}개)")
            print()
            
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}\n")
    
    retriever.close()
    print("✅ 전체 파이프라인 테스트 완료\n")


def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("RAG 시스템 테스트 시작")
    print("=" * 60 + "\n")
    
    # 1. Vector DB 검색 테스트 (API 키 불필요)
    test_retriever()
    
    # 2. LLM 답변 생성 테스트 (API 키 필요)
    test_generator()
    
    # 3. 전체 파이프라인 테스트 (API 키 필요)
    test_full_pipeline()
    
    print("=" * 60)
    print("모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
