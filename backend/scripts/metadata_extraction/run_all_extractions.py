#!/usr/bin/env python3
"""
모든 데이터 소스의 메타데이터 추출 통합 실행 스크립트
"""

import sys
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

from extract_law_metadata import LawMetadataExtractor, DB_CONFIG
from extract_criteria_metadata import CriteriaMetadataExtractor
from extract_case_metadata import CaseMetadataExtractor


def main():
    """전체 메타데이터 추출 프로세스"""
    
    print("="*60)
    print("전체 메타데이터 추출 시작")
    print("="*60)
    print()
    
    success_count = 0
    total_count = 3
    
    # 1. 법령 메타데이터 추출
    try:
        print("\n" + "#"*60)
        print("# 1/3: 법령 메타데이터 추출")
        print("#"*60)
        law_extractor = LawMetadataExtractor(DB_CONFIG)
        law_extractor.run()
        success_count += 1
    except Exception as e:
        print(f"❌ 법령 메타데이터 추출 실패: {e}")
    
    # 2. 기준 메타데이터 추출
    try:
        print("\n" + "#"*60)
        print("# 2/3: 기준 메타데이터 추출")
        print("#"*60)
        criteria_extractor = CriteriaMetadataExtractor(DB_CONFIG)
        criteria_extractor.run()
        success_count += 1
    except Exception as e:
        print(f"❌ 기준 메타데이터 추출 실패: {e}")
    
    # 3. 사례 메타데이터 추출
    try:
        print("\n" + "#"*60)
        print("# 3/3: 사례 메타데이터 추출")
        print("#"*60)
        case_extractor = CaseMetadataExtractor(DB_CONFIG)
        case_extractor.run()
        success_count += 1
    except Exception as e:
        print(f"❌ 사례 메타데이터 추출 실패: {e}")
    
    # 최종 결과
    print("\n" + "="*60)
    print("전체 메타데이터 추출 완료")
    print("="*60)
    print(f"성공: {success_count}/{total_count}")
    if success_count == total_count:
        print("✅ 모든 메타데이터 추출이 성공적으로 완료되었습니다!")
    else:
        print(f"⚠️  일부 메타데이터 추출이 실패했습니다.")
    print("="*60)
    
    return success_count == total_count


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
