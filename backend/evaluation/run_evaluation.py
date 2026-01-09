"""
똑소리 프로젝트 - RAG 평가 실행 스크립트
작성일: 2026-01-05

사용법:
  python run_evaluation.py --dataset datasets/gold_v1.json --methods vector hybrid multi_source
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.retriever import RAGRetriever
from evaluation.evaluator import RAGEvaluator


def parse_args():
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(description="RAG 시스템 정량 평가")
    
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="골드 데이터셋 경로 (예: datasets/gold_v1.json)"
    )
    
    parser.add_argument(
        "--methods",
        nargs="+",
        default=["vector", "hybrid", "multi_source"],
        choices=["vector", "hybrid", "multi_source"],
        help="평가할 검색 방법 (기본: vector hybrid multi_source)"
    )
    
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="검색할 청크 수 (기본: 10)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/results",
        help="결과 저장 디렉토리 (기본: evaluation/results)"
    )
    
    parser.add_argument(
        "--db-host",
        type=str,
        default=None,
        help="데이터베이스 호스트 (기본: 환경변수 DB_HOST)"
    )
    
    parser.add_argument(
        "--db-port",
        type=str,
        default=None,
        help="데이터베이스 포트 (기본: 환경변수 DB_PORT)"
    )
    
    parser.add_argument(
        "--db-name",
        type=str,
        default=None,
        help="데이터베이스 이름 (기본: 환경변수 DB_NAME)"
    )
    
    parser.add_argument(
        "--embed-api-url",
        type=str,
        default=None,
        help="임베딩 API URL (기본: 환경변수 EMBED_API_URL)"
    )
    
    return parser.parse_args()


def main():
    """메인 실행 함수"""
    # 환경 변수 로드
    load_dotenv()
    
    # 인자 파싱
    args = parse_args()
    
    # 데이터셋 경로 확인
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"❌ 데이터셋을 찾을 수 없습니다: {dataset_path}")
        sys.exit(1)
    
    # 데이터베이스 설정
    db_config = {
        'host': args.db_host or os.getenv('DB_HOST', 'localhost'),
        'port': args.db_port or os.getenv('DB_PORT', '5432'),
        'database': args.db_name or os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # 임베딩 API URL
    embed_api_url = args.embed_api_url or os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
    
    print("=" * 80)
    print("똑소리 프로젝트 - RAG 시스템 정량 평가")
    print("=" * 80)
    print(f"데이터셋: {dataset_path}")
    print(f"검색 방법: {', '.join(args.methods)}")
    print(f"Top-K: {args.top_k}")
    print(f"출력 디렉토리: {args.output_dir}")
    print(f"데이터베이스: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    print(f"임베딩 API: {embed_api_url}")
    print("=" * 80)
    print()
    
    # RAG Retriever 초기화
    print("[1/3] RAG Retriever 초기화 중...")
    retriever = RAGRetriever(db_config, embed_api_url)
    retriever.connect()
    print("✅ RAG Retriever 초기화 완료")
    
    try:
        # Evaluator 초기화
        print("\n[2/3] Evaluator 초기화 중...")
        evaluator = RAGEvaluator(retriever, str(dataset_path))
        evaluator.load_dataset()
        print("✅ Evaluator 초기화 완료")
        
        # 평가 실행
        print("\n[3/3] 평가 실행 중...")
        all_results = evaluator.evaluate_all(
            search_methods=args.methods,
            top_k=args.top_k
        )
        
        # 결과 저장
        json_path, summary_path = evaluator.save_results(all_results, args.output_dir)
        
        # 요약 출력
        evaluator.print_summary(all_results)
        
        print("\n" + "=" * 80)
        print("평가 완료!")
        print("=" * 80)
        print(f"상세 결과: {json_path}")
        print(f"요약 통계: {summary_path}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        retriever.close()


if __name__ == "__main__":
    main()
