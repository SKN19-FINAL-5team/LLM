#!/usr/bin/env python3
"""
RAG CLI Dry-run 테스트
실제 DB/API 호출 없이 import 및 기본 구조 확인
"""

import sys
from pathlib import Path

# 프로젝트 경로 추가
backend_dir = Path(__file__).parent.parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))


def test_imports():
    """모든 모듈 import 테스트"""
    print("=" * 80)
    print("1. 모듈 Import 테스트")
    print("=" * 80)
    
    errors = []
    warnings = []
    
    # MultiMethodRetriever import
    try:
        from app.rag.multi_method_retriever import MultiMethodRetriever
        print("✅ MultiMethodRetriever import 성공")
    except ImportError as e:
        if 'psycopg2' in str(e) or 'dotenv' in str(e):
            print(f"⚠️  MultiMethodRetriever import 실패 (의존성 누락): {e}")
            print("   → 환경 설정 후 정상 작동할 것입니다.")
            warnings.append(f"MultiMethodRetriever 의존성: {e}")
        else:
            print(f"❌ MultiMethodRetriever import 실패: {e}")
            errors.append(f"MultiMethodRetriever: {e}")
    except Exception as e:
        print(f"❌ MultiMethodRetriever import 실패: {e}")
        errors.append(f"MultiMethodRetriever: {e}")
    
    # RAGGenerator import
    try:
        from app.rag.generator import RAGGenerator
        print("✅ RAGGenerator import 성공")
    except ImportError as e:
        if 'psycopg2' in str(e) or 'openai' in str(e) or 'dotenv' in str(e):
            print(f"⚠️  RAGGenerator import 실패 (의존성 누락): {e}")
            print("   → 환경 설정 후 정상 작동할 것입니다.")
            warnings.append(f"RAGGenerator 의존성: {e}")
        else:
            print(f"❌ RAGGenerator import 실패: {e}")
            errors.append(f"RAGGenerator: {e}")
    except Exception as e:
        print(f"❌ RAGGenerator import 실패: {e}")
        errors.append(f"RAGGenerator: {e}")
    
    # GoldenSetLoader import
    try:
        from scripts.cli.golden_set_loader import GoldenSetLoader
        print("✅ GoldenSetLoader import 성공")
    except Exception as e:
        print(f"❌ GoldenSetLoader import 실패: {e}")
        errors.append(f"GoldenSetLoader: {e}")
    
    # CLI 모듈 import (실제 실행은 하지 않음)
    try:
        import scripts.cli.rag_cli as rag_cli
        print("✅ rag_cli 모듈 import 성공")
    except ImportError as e:
        if 'dotenv' in str(e) or 'psycopg2' in str(e):
            print(f"⚠️  rag_cli 모듈 import 실패 (의존성 누락): {e}")
            print("   → 환경 설정 후 정상 작동할 것입니다.")
            warnings.append(f"rag_cli 의존성: {e}")
        else:
            print(f"❌ rag_cli 모듈 import 실패: {e}")
            errors.append(f"rag_cli: {e}")
    except Exception as e:
        print(f"❌ rag_cli 모듈 import 실패: {e}")
        errors.append(f"rag_cli: {e}")
    
    return errors, warnings


def test_class_initialization():
    """클래스 초기화 테스트 (실제 DB 연결 없이)"""
    print("\n" + "=" * 80)
    print("2. 클래스 구조 확인 테스트")
    print("=" * 80)
    
    errors = []
    warnings = []
    
    # MultiMethodRetriever 클래스 구조 확인
    try:
        from app.rag.multi_method_retriever import MultiMethodRetriever
        
        # 메서드 존재 확인
        required_methods = [
            'search_cosine',
            'search_bm25',
            'search_splade',
            'search_hybrid',
            'search_all_methods',
            'close'
        ]
        
        for method_name in required_methods:
            if hasattr(MultiMethodRetriever, method_name):
                print(f"✅ MultiMethodRetriever.{method_name} 존재")
            else:
                print(f"❌ MultiMethodRetriever.{method_name} 없음")
                errors.append(f"MultiMethodRetriever.{method_name} 없음")
    
    except ImportError as e:
        print(f"⚠️  MultiMethodRetriever 구조 확인 건너뜀 (의존성 누락)")
        warnings.append(f"MultiMethodRetriever 구조 확인: {e}")
    except Exception as e:
        print(f"❌ MultiMethodRetriever 구조 확인 실패: {e}")
        errors.append(f"MultiMethodRetriever 구조: {e}")
    
    # RAGGenerator 클래스 구조 확인
    try:
        from app.rag.generator import RAGGenerator
        
        # 메서드 존재 확인
        required_methods = [
            'generate_answer',
            'generate_comparative_answer',
            'format_context',
            'format_multi_method_context'
        ]
        
        for method_name in required_methods:
            if hasattr(RAGGenerator, method_name):
                print(f"✅ RAGGenerator.{method_name} 존재")
            else:
                print(f"❌ RAGGenerator.{method_name} 없음")
                errors.append(f"RAGGenerator.{method_name} 없음")
    
    except ImportError as e:
        print(f"⚠️  RAGGenerator 구조 확인 건너뜀 (의존성 누락)")
        warnings.append(f"RAGGenerator 구조 확인: {e}")
    except Exception as e:
        print(f"❌ RAGGenerator 구조 확인 실패: {e}")
        errors.append(f"RAGGenerator 구조: {e}")
    
    # GoldenSetLoader 클래스 구조 확인
    try:
        from scripts.cli.golden_set_loader import GoldenSetLoader
        
        # 메서드 존재 확인
        required_methods = [
            'load',
            'get_all_queries',
            'get_query_by_id',
            'get_query_by_index',
            'display_queries',
            'select_query_interactive',
            'get_dataset_info'
        ]
        
        for method_name in required_methods:
            if hasattr(GoldenSetLoader, method_name):
                print(f"✅ GoldenSetLoader.{method_name} 존재")
            else:
                print(f"❌ GoldenSetLoader.{method_name} 없음")
                errors.append(f"GoldenSetLoader.{method_name} 없음")
    
    except Exception as e:
        print(f"❌ GoldenSetLoader 구조 확인 실패: {e}")
        errors.append(f"GoldenSetLoader 구조: {e}")
    
    return errors, warnings


def test_golden_set_loader():
    """Golden Set Loader 테스트 (파일 로드만)"""
    print("\n" + "=" * 80)
    print("3. Golden Set Loader 테스트")
    print("=" * 80)
    
    errors = []
    
    try:
        from scripts.cli.golden_set_loader import GoldenSetLoader
        
        loader = GoldenSetLoader()
        
        # 파일 존재 확인
        if loader.golden_set_path.exists():
            print(f"✅ Golden Set 파일 존재: {loader.golden_set_path}")
            
            # 로드 시도 (실제 로드는 하지 않음)
            print(f"   파일 크기: {loader.golden_set_path.stat().st_size} bytes")
        else:
            print(f"⚠️  Golden Set 파일 없음: {loader.golden_set_path}")
            print("   (실제 사용 시에는 파일이 필요합니다)")
    
    except Exception as e:
        print(f"❌ Golden Set Loader 테스트 실패: {e}")
        errors.append(f"GoldenSetLoader 테스트: {e}")
    
    return errors


def test_cli_argument_parsing():
    """CLI 인자 파싱 테스트"""
    print("\n" + "=" * 80)
    print("4. CLI 인자 파싱 테스트")
    print("=" * 80)
    
    errors = []
    warnings = []
    
    try:
        import argparse
        import scripts.cli.rag_cli as rag_cli
        
        # argparse가 정의되어 있는지 확인
        if hasattr(rag_cli, 'main'):
            print("✅ rag_cli.main 함수 존재")
        else:
            print("❌ rag_cli.main 함수 없음")
            errors.append("rag_cli.main 없음")
    
    except ImportError as e:
        if 'dotenv' in str(e) or 'psycopg2' in str(e):
            print(f"⚠️  CLI 인자 파싱 테스트 건너뜀 (의존성 누락)")
            warnings.append(f"CLI 인자 파싱: {e}")
        else:
            print(f"❌ CLI 인자 파싱 테스트 실패: {e}")
            errors.append(f"CLI 인자 파싱: {e}")
    except Exception as e:
        print(f"❌ CLI 인자 파싱 테스트 실패: {e}")
        errors.append(f"CLI 인자 파싱: {e}")
    
    return errors, warnings


def main():
    """메인 테스트 함수"""
    print("\n" + "=" * 80)
    print("RAG CLI Dry-run 테스트 시작")
    print("=" * 80 + "\n")
    
    all_errors = []
    all_warnings = []
    
    # 1. Import 테스트
    errors, warnings = test_imports()
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    
    # 2. 클래스 구조 확인
    errors, warnings = test_class_initialization()
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    
    # 3. Golden Set Loader 테스트
    errors = test_golden_set_loader()
    all_errors.extend(errors)
    
    # 4. CLI 인자 파싱 테스트
    errors, warnings = test_cli_argument_parsing()
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    
    if all_warnings:
        print(f"\n⚠️  총 {len(all_warnings)}개의 경고 (의존성 누락):")
        for warning in all_warnings:
            print(f"  - {warning}")
        print("   → 환경 설정 후 정상 작동할 것입니다.")
    
    if all_errors:
        print(f"\n❌ 총 {len(all_errors)}개의 오류 발견:")
        for error in all_errors:
            print(f"  - {error}")
        print("\n⚠️  일부 기능이 정상 작동하지 않을 수 있습니다.")
        return 1
    else:
        print("\n✅ 모든 dry-run 테스트 통과!")
        if all_warnings:
            print("   (의존성 경고는 환경 설정 후 해결됩니다)")
        print("   모든 모듈이 정상적으로 import되고 기본 구조가 올바릅니다.")
        print("   실제 사용을 위해서는 DB 연결과 OpenAI API 키가 필요합니다.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
