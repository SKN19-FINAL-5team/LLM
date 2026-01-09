#!/usr/bin/env python3
"""
RAG CLI Interface
사용자가 CLI에서 질문을 입력하면, 여러 검색 방법으로 결과를 검색하고
LLM이 이를 비교 분석하여 최종 답변을 생성하는 CLI 도구
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 프로젝트 경로 추가
backend_dir = Path(__file__).parent.parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from app.rag.multi_method_retriever import MultiMethodRetriever
from app.rag.generator import RAGGenerator
from scripts.cli.golden_set_loader import GoldenSetLoader

# 환경 변수 로드
load_dotenv()


def format_output(answer: str, metadata: dict) -> str:
    """
    답변을 보기 좋게 포맷팅
    
    Args:
        answer: LLM이 생성한 답변
        metadata: 메타데이터 (모델, 토큰 사용량 등)
    
    Returns:
        포맷팅된 문자열
    """
    output = []
    output.append("\n" + "=" * 80)
    output.append("답변")
    output.append("=" * 80)
    output.append(answer)
    output.append("\n" + "-" * 80)
    output.append("메타데이터")
    output.append("-" * 80)
    output.append(f"모델: {metadata.get('model', 'N/A')}")
    output.append(f"사용된 검색 방법: {', '.join(metadata.get('methods_used', []))}")
    output.append(f"총 검색 결과 수: {metadata.get('total_results', 0)}개")
    
    if 'usage' in metadata:
        usage = metadata['usage']
        output.append(f"토큰 사용량:")
        output.append(f"  - 프롬프트: {usage.get('prompt_tokens', 0)}")
        output.append(f"  - 완성: {usage.get('completion_tokens', 0)}")
        output.append(f"  - 총합: {usage.get('total_tokens', 0)}")
    
    output.append("=" * 80)
    
    return "\n".join(output)


def run_query(
    query: str,
    db_config: dict,
    top_k: int = 10,
    methods: Optional[list] = None,
    model: str = "gpt-4o-mini"
) -> dict:
    """
    단일 쿼리 실행
    
    Args:
        query: 사용자 질문
        db_config: 데이터베이스 설정
        top_k: 각 검색 방법별 반환할 최대 결과 수
        methods: 실행할 검색 방법 리스트 (None이면 모두 실행)
        model: 사용할 LLM 모델
    
    Returns:
        결과 딕셔너리
    """
    print(f"\n{'='*80}")
    print(f"질문: {query}")
    print(f"{'='*80}\n")
    
    # 1. MultiMethodRetriever 초기화
    print("🔧 검색 시스템 초기화 중...")
    retriever = MultiMethodRetriever(db_config)
    
    # 2. 모든 검색 방법 실행
    print(f"\n🔍 검색 실행 중... (top_k={top_k})")
    method_results = retriever.search_all_methods(
        query=query,
        top_k=top_k,
        methods=methods
    )
    
    # 검색 결과 요약
    print("\n검색 결과 요약:")
    for method_name, method_data in method_results.get('methods', {}).items():
        if method_data.get('success', False):
            count = method_data.get('count', 0)
            elapsed = method_data.get('elapsed_time', 0)
            print(f"  ✅ {method_name.upper()}: {count}개 결과 ({elapsed:.3f}초)")
        else:
            error = method_data.get('error', 'Unknown error')
            print(f"  ❌ {method_name.upper()}: 실패 - {error}")
    
    # 3. LLM으로 답변 생성
    print("\n🤖 LLM 답변 생성 중...")
    generator = RAGGenerator(model=model)
    
    result = generator.generate_comparative_answer(
        query=query,
        method_results=method_results
    )
    
    # 4. 결과 출력
    output = format_output(result['answer'], result)
    print(output)
    
    # 리소스 정리
    retriever.close()
    
    return result


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='RAG CLI - 여러 검색 방법을 통합하여 LLM 답변 생성',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 직접 질문 입력
  python rag_cli.py --query "냉장고 무상 수리 가능한가요?"
  
  # Golden set에서 선택
  python rag_cli.py --golden-set
  
  # 특정 검색 방법만 사용
  python rag_cli.py --query "질문" --methods cosine hybrid
  
  # Top-K 조정
  python rag_cli.py --query "질문" --top-k 5
        """
    )
    
    parser.add_argument(
        '--query', '-q',
        type=str,
        help='사용자 질문 (직접 입력)'
    )
    
    parser.add_argument(
        '--golden-set', '-g',
        action='store_true',
        help='Golden set에서 쿼리 선택'
    )
    
    parser.add_argument(
        '--top-k', '-k',
        type=int,
        default=10,
        help='각 검색 방법별 반환할 최대 결과 수 (기본값: 10)'
    )
    
    parser.add_argument(
        '--methods', '-m',
        nargs='+',
        choices=['cosine', 'bm25', 'splade', 'hybrid'],
        help='실행할 검색 방법 선택 (기본값: 모두 실행)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-4o-mini',
        help='사용할 LLM 모델 (기본값: gpt-4o-mini)'
    )
    
    parser.add_argument(
        '--golden-set-path',
        type=str,
        help='Golden set JSON 파일 경로 (기본값: backend/evaluation/datasets/gold_real_consumer_cases.json)'
    )
    
    args = parser.parse_args()
    
    # OpenAI API 키 확인
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 실제 API 키를 입력하세요.")
        sys.exit(1)
    
    # DB 설정
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # 쿼리 결정
    query = None
    
    if args.golden_set:
        # Golden set에서 선택
        golden_set_path = Path(args.golden_set_path) if args.golden_set_path else None
        loader = GoldenSetLoader(golden_set_path)
        
        selected = loader.select_query_interactive()
        
        if selected is None:
            print("쿼리 선택이 취소되었습니다.")
            sys.exit(0)
        
        if isinstance(selected, dict) and selected.get('all'):
            # 모든 쿼리 실행 (배치 모드)
            queries = selected['queries']
            print(f"\n총 {len(queries)}개 쿼리를 실행합니다.\n")
            
            for idx, test_case in enumerate(queries, 1):
                query = test_case.get('query')
                query_id = test_case.get('query_id', f'Q{idx:03d}')
                
                print(f"\n{'#'*80}")
                print(f"# 쿼리 {idx}/{len(queries)}: {query_id}")
                print(f"{'#'*80}")
                
                try:
                    run_query(
                        query=query,
                        db_config=db_config,
                        top_k=args.top_k,
                        methods=args.methods,
                        model=args.model
                    )
                except Exception as e:
                    print(f"\n❌ 오류 발생: {e}")
                    continue
        else:
            # 단일 쿼리 선택
            query = selected.get('query')
            if not query:
                print("❌ 쿼리를 찾을 수 없습니다.")
                sys.exit(1)
    
    elif args.query:
        # 직접 질문 입력
        query = args.query
    
    else:
        # 대화형 모드: 직접 입력
        print("\nRAG CLI - 질문을 입력하세요 (종료: Ctrl+C 또는 'quit')")
        print("-" * 80)
        
        try:
            query = input("\n질문: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("종료합니다.")
                sys.exit(0)
            
            if not query:
                print("❌ 질문을 입력하세요.")
                sys.exit(1)
        
        except KeyboardInterrupt:
            print("\n\n종료합니다.")
            sys.exit(0)
    
    # 쿼리 실행
    try:
        run_query(
            query=query,
            db_config=db_config,
            top_k=args.top_k,
            methods=args.methods,
            model=args.model
        )
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
