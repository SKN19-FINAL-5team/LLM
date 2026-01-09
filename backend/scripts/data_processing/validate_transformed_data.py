#!/usr/bin/env python3
"""
변환된 데이터 검증 스크립트

변환된 JSON 데이터를 검토하여 임베딩 진행 가능 여부 판단
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# 스크립트 위치 기준으로 프로젝트 루트 찾기
SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/data_processing/
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # ddoksori_demo/
DATA_DIR = PROJECT_ROOT / "backend" / "data"

# 청크 타입별 처리 규칙 (data_transform_pipeline.py와 동일)
CHUNK_PROCESSING_RULES = {
    'decision': {
        'min_length': 50,
        'max_length': 800,
        'drop_if_empty': True
    },
    'reasoning': {
        'min_length': 100,
        'max_length': 1500,
    },
    'judgment': {
        'min_length': 200,
        'max_length': 1500,
    },
    'law': {
        'min_length': 30,
        'max_length': 2000,
        'drop_if_empty': True,
    },
    'law_reference': {
        'min_length': 20,
        'max_length': 2000,
        'drop_if_empty': True
    },
    'resolution_row': {
        'min_length': 50,
        'max_length': 2000,
    },
    'qa_combined': {
        'min_length': 100,
        'max_length': 1500,
    },
    # 기본 규칙
    'default': {
        'min_length': 100,
        'max_length': 1500,
        'drop_if_empty': True
    }
}

# 청크 타입별 처리 규칙
CHUNK_PROCESSING_RULES = {
    'decision': {
        'min_length': 50,
        'max_length': 800,
        'merge_allowed': False,  # 결정문은 독립성 유지
        'drop_if_empty': True,
        'description': '결정문'
    },
    'reasoning': {
        'min_length': 100,
        'max_length': 1500,
        'merge_allowed': True,
        'split_allowed': True,
        'description': '판단 근거'
    },
    'judgment': {
        'min_length': 200,
        'max_length': 1500,
        'split_allowed': True,  # 긴 판단 내용 분할
        'description': '판단 내용'
    },
    'law': {
        'min_length': 30,
        'max_length': 2000,
        'drop_if_empty': True,
        'enrich_with_metadata': True,  # 메타데이터로 내용 보강
        'description': '관련 법령'
    },
    'summary': {
        'min_length': 50,
        'max_length': 1000,
        'description': '요약'
    },
    'full_text': {
        'min_length': 100,
        'max_length': 2000,
        'split_allowed': True,
        'description': '전문'
    },
    'case_info': {
        'min_length': 30,
        'max_length': 1000,
        'description': '사건 정보'
    },
    'default': {
        'min_length': 50,
        'max_length': 1500,
        'description': '기타'
    }
}


def has_meaningful_content(content: str) -> bool:
    """의미 있는 내용인지 체크"""
    if not content or not content.strip():
        return False
    
    # 공백 제거
    cleaned = content.strip()
    
    # 1. 너무 짧은 경우
    if len(cleaned) < 5:
        return False
    
    # 2. 의미 없는 패턴들
    meaningless_patterns = [
        r'^[가-힣]\.$',  # 단일 문자 + 마침표 (예: "가.", "나.")
        r'^[0-9]+\.$',   # 숫자 + 마침표 (예: "1.", "2.")
        r'^[\s\n\r\t]+$',  # 공백만
        r'^[-=_*#]+$',   # 구분선만
    ]
    
    for pattern in meaningless_patterns:
        if re.match(pattern, cleaned):
            return False
    
    # 3. 한글/영문 문자가 최소 5자 이상 있어야 함
    text_chars = re.findall(r'[가-힣a-zA-Z]', cleaned)
    if len(text_chars) < 5:
        return False
    
    return True


def estimate_token_count(text: str) -> int:
    """
    토큰 수 추정 (한국어 기준)
    
    한국어 토큰 변환율: 약 1.5-2자 = 1토큰
    보수적 추정: 1.5자 = 1토큰
    
    Args:
        text: 토큰 수를 추정할 텍스트
        
    Returns:
        추정된 토큰 수
    """
    return int(len(text) / 1.5)


def validate_token_limits(chunks: List[Dict], max_tokens: int = 512) -> Dict:
    """
    토큰 제한 검증
    
    Args:
        chunks: 검증할 청크 리스트
        max_tokens: 최대 토큰 수 (기본: 512, KURE-v1 모델 제한)
        
    Returns:
        {
            'violations': List[Dict],
            'stats_by_type': Dict,
            'total_violations': int
        }
    """
    violations = []
    stats_by_type = defaultdict(lambda: {
        'count': 0,
        'avg_tokens': 0,
        'max_tokens': 0,
        'violation_count': 0
    })
    
    for chunk in chunks:
        if chunk.get('drop', False):
            continue
        
        chunk_type = chunk.get('chunk_type', 'unknown')
        content = chunk.get('content', '')
        estimated_tokens = estimate_token_count(content)
        
        stats = stats_by_type[chunk_type]
        stats['count'] += 1
        stats['avg_tokens'] = (stats['avg_tokens'] * (stats['count'] - 1) + estimated_tokens) / stats['count']
        stats['max_tokens'] = max(stats['max_tokens'], estimated_tokens)
        
        if estimated_tokens > max_tokens:
            stats['violation_count'] += 1
            violations.append({
                'chunk_id': chunk.get('chunk_id'),
                'chunk_type': chunk_type,
                'char_count': len(content),
                'estimated_tokens': estimated_tokens,
                'excess_tokens': estimated_tokens - max_tokens
            })
    
    return {
        'violations': violations,
        'stats_by_type': dict(stats_by_type),
        'total_violations': len(violations)
    }


def check_encoding_quality(content: str) -> Tuple[bool, str]:
    """인코딩 가능 여부 및 품질 체크"""
    if not content:
        return False, "빈 콘텐츠"
    
    try:
        # UTF-8 인코딩 가능 여부
        content.encode('utf-8')
    except UnicodeEncodeError as e:
        return False, f"UTF-8 인코딩 오류: {e}"
    
    # 특수 문자 비율 체크 (너무 높으면 깨진 텍스트일 가능성)
    total_chars = len(content)
    if total_chars == 0:
        return False, "빈 콘텐츠"
    
    # 일반 문자 (한글, 영문, 숫자, 공백, 기본 문장부호)
    normal_chars = len(re.findall(r'[가-힣a-zA-Z0-9\s.,!?;:()\[\]{}"\'-]', content))
    normal_ratio = normal_chars / total_chars
    
    if normal_ratio < 0.8:  # 정상 문자가 80% 미만이면 의심
        return False, f"비정상 문자 비율 높음 ({normal_ratio:.1%})"
    
    return True, "정상"

class TransformedDataValidator:
    """변환된 데이터 검증"""
    
    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = DATA_DIR / "transformed"
        self.data_dir = Path(data_dir)
        self.issues = []
        self.warnings = []
        self.stats = defaultdict(int)
    
    def load_all_data(self) -> Dict[str, Dict]:
        """모든 변환된 JSON 파일 로드"""
        data = {}
        
        json_files = list(self.data_dir.glob('*.json'))
        if not json_files:
            print(f"❌ {self.data_dir}에 JSON 파일이 없습니다.")
            return data
        
        for json_file in json_files:
            if json_file.name == 'transformation_summary.json':
                continue
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data[json_file.stem] = json.load(f)
                print(f"✅ 로드: {json_file.name}")
            except Exception as e:
                print(f"❌ 로드 실패: {json_file.name} - {e}")
        
        return data
    
    def validate_chunk_indices(self, doc_data: Dict) -> bool:
        """chunk_index 검증"""
        doc_id = doc_data['doc_id']
        chunks = doc_data['chunks']
        
        is_valid = True
        
        # 1. chunk_index가 0부터 시작하는지
        min_index = min(c['chunk_index'] for c in chunks)
        if min_index != 0:
            self.issues.append(
                f"❌ {doc_id}: chunk_index가 0부터 시작하지 않음 (시작: {min_index})"
            )
            is_valid = False
        
        # 2. chunk_index가 연속적인지
        indices = sorted(c['chunk_index'] for c in chunks)
        expected_indices = list(range(len(chunks)))
        if indices != expected_indices:
            self.issues.append(
                f"❌ {doc_id}: chunk_index가 연속적이지 않음\n"
                f"   Expected: {expected_indices}\n"
                f"   Actual: {indices}"
            )
            is_valid = False
        
        # 3. chunk_total이 일치하는지
        for chunk in chunks:
            if chunk['chunk_total'] != len(chunks):
                self.issues.append(
                    f"❌ {doc_id}: chunk_total 불일치\n"
                    f"   chunk_id: {chunk['chunk_id']}\n"
                    f"   Expected: {len(chunks)}\n"
                    f"   Actual: {chunk['chunk_total']}"
                )
                is_valid = False
                break
        
        # 4. chunk_index < chunk_total 확인
        for chunk in chunks:
            if chunk['chunk_index'] >= chunk['chunk_total']:
                self.issues.append(
                    f"❌ {doc_id}: chunk_index >= chunk_total\n"
                    f"   chunk_id: {chunk['chunk_id']}\n"
                    f"   chunk_index: {chunk['chunk_index']}\n"
                    f"   chunk_total: {chunk['chunk_total']}"
                )
                is_valid = False
                break
        
        return is_valid
    
    def validate_required_fields(self, doc_data: Dict) -> bool:
        """필수 필드 확인"""
        doc_id = doc_data['doc_id']
        is_valid = True
        
        # 문서 필수 필드
        doc_required = ['doc_id', 'doc_type', 'title', 'source_org', 'chunks']
        for field in doc_required:
            if field not in doc_data:
                self.issues.append(f"❌ {doc_id}: 문서에 '{field}' 필드 없음")
                is_valid = False
        
        # 청크 필수 필드
        chunk_required = ['chunk_id', 'chunk_index', 'chunk_total', 'chunk_type', 'content', 'content_length', 'drop']
        for chunk in doc_data.get('chunks', []):
            for field in chunk_required:
                if field not in chunk:
                    self.issues.append(
                        f"❌ {doc_id}: 청크 {chunk.get('chunk_id', 'unknown')}에 '{field}' 필드 없음"
                    )
                    is_valid = False
                    break
        
        return is_valid
    
    def validate_content_quality(self, doc_data: Dict) -> bool:
        """강화된 콘텐츠 품질 검증"""
        doc_id = doc_data['doc_id']
        is_valid = True
        
        for chunk in doc_data.get('chunks', []):
            content = chunk.get('content', '')
            content_length = chunk.get('content_length', 0)
            chunk_type = chunk.get('chunk_type', 'default')
            chunk_id = chunk.get('chunk_id', 'unknown')
            should_drop = chunk.get('drop', False)
            
            # 청크 타입별 규칙 가져오기
            rules = CHUNK_PROCESSING_RULES.get(chunk_type, CHUNK_PROCESSING_RULES['default'])
            min_length = rules['min_length']
            max_length = rules['max_length']
            
            # 1. 빈 콘텐츠 체크 (Critical)
            if not content or not content.strip():
                # drop=True인 경우는 허용
                if should_drop:
                    self.stats[f'dropped_empty_{chunk_type}'] += 1
                elif rules.get('drop_if_empty', False):
                    self.warnings.append(
                        f"⚠️  {doc_id}: 빈 content (drop=True로 설정 권장)\n"
                        f"   chunk_id: {chunk_id}\n"
                        f"   chunk_type: {chunk_type}"
                    )
                else:
                    self.issues.append(
                        f"❌ {doc_id}: content가 비어있음\n"
                        f"   chunk_id: {chunk_id}\n"
                        f"   chunk_type: {chunk_type}"
                    )
                    is_valid = False
                continue
            
            # 2. 인코딩 품질 체크 (Critical)
            encoding_ok, encoding_msg = check_encoding_quality(content)
            if not encoding_ok:
                self.issues.append(
                    f"❌ {doc_id}: 인코딩 오류\n"
                    f"   chunk_id: {chunk_id}\n"
                    f"   오류: {encoding_msg}"
                )
                is_valid = False
                continue
            
            # 3. 의미 있는 내용 체크
            if not has_meaningful_content(content):
                if should_drop:
                    self.stats[f'dropped_meaningless_{chunk_type}'] += 1
                else:
                    self.warnings.append(
                        f"⚠️  {doc_id}: 의미 없는 내용 (drop=True 권장)\n"
                        f"   chunk_id: {chunk_id}\n"
                        f"   content: {content[:100]}"
                    )
            
            # 4. 타입별 최소 길이 체크
            if content_length < min_length and not should_drop:
                severity = "경고" if rules.get('merge_allowed', False) else "주의"
                self.warnings.append(
                    f"⚠️  {doc_id}: 청크가 최소 길이 미달 ({severity})\n"
                    f"   chunk_id: {chunk_id}\n"
                    f"   chunk_type: {chunk_type} (최소: {min_length}자)\n"
                    f"   실제 길이: {content_length}자\n"
                    f"   내용: {content[:100]}"
                )
                self.stats[f'too_short_{chunk_type}'] += 1
            
            # 5. 타입별 최대 길이 체크
            if content_length > max_length:
                severity = "권장" if rules.get('split_allowed', False) else "주의"
                self.warnings.append(
                    f"⚠️  {doc_id}: 청크가 최대 길이 초과 ({severity} 분할)\n"
                    f"   chunk_id: {chunk_id}\n"
                    f"   chunk_type: {chunk_type} (최대: {max_length}자)\n"
                    f"   실제 길이: {content_length:,}자"
                )
                self.stats[f'too_long_{chunk_type}'] += 1
            
            # 6. content_length가 실제 길이와 다름
            actual_length = len(content)
            if abs(actual_length - content_length) > 5:  # 5자 이상 차이
                self.warnings.append(
                    f"⚠️  {doc_id}: content_length 불일치\n"
                    f"   chunk_id: {chunk_id}\n"
                    f"   Expected: {content_length}\n"
                    f"   Actual: {actual_length}"
                )
            
            # 7. RAG 최적 범위 체크 (100-2000자)
            if not should_drop:
                if 100 <= content_length <= 2000:
                    self.stats['optimal_chunks'] += 1
                elif content_length < 100:
                    self.stats['suboptimal_too_short'] += 1
                else:
                    self.stats['suboptimal_too_long'] += 1
        
        return is_valid
    
    def validate_document(self, doc_data: Dict) -> bool:
        """단일 문서 검증"""
        doc_id = doc_data.get('doc_id', 'unknown')
        
        # 1. 필수 필드 확인
        if not self.validate_required_fields(doc_data):
            return False
        
        # 2. chunk_index 검증
        if not self.validate_chunk_indices(doc_data):
            return False
        
        # 3. 콘텐츠 품질 검증
        if not self.validate_content_quality(doc_data):
            return False
        
        # 통계 수집
        self.stats['total_documents'] += 1
        self.stats['total_chunks'] += len(doc_data.get('chunks', []))
        self.stats[f"doc_type_{doc_data['doc_type']}"] += 1
        self.stats[f"source_org_{doc_data['source_org']}"] += 1
        
        return True
    
    def validate_all(self, data: Dict[str, Dict]) -> Tuple[bool, Dict]:
        """모든 데이터 검증"""
        print("\n" + "=" * 80)
        print("변환 데이터 검증 시작")
        print("=" * 80)
        
        all_valid = True
        
        for file_name, file_data in data.items():
            print(f"\n📄 검증: {file_name}")
            
            documents = file_data.get('documents', [])
            print(f"  - 문서 수: {len(documents)}개")
            
            for doc_data in documents:
                doc_valid = self.validate_document(doc_data)
                if not doc_valid:
                    all_valid = False
        
        # 토큰 제한 검증
        print("\n🔬 토큰 제한 검증 (KURE-v1 모델: 512 토큰)")
        all_chunks = []
        for file_name, file_data in data.items():
            for doc_data in file_data.get('documents', []):
                all_chunks.extend(doc_data.get('chunks', []))
        
        token_validation = validate_token_limits(all_chunks)
        
        print(f"  - 총 청크: {len([c for c in all_chunks if not c.get('drop', False)]):,}개")
        print(f"  - 토큰 초과: {token_validation['total_violations']:,}개")
        
        if token_validation['total_violations'] > 0:
            print(f"\n  ⚠️  토큰 초과 청크 타입별 분석:")
            for chunk_type, stats in sorted(token_validation['stats_by_type'].items()):
                if stats['violation_count'] > 0:
                    violation_rate = stats['violation_count'] / stats['count'] * 100
                    print(f"    • {chunk_type}: {stats['violation_count']}/{stats['count']} ({violation_rate:.1f}%)")
                    print(f"      - 평균 토큰: {stats['avg_tokens']:.0f}")
                    print(f"      - 최대 토큰: {stats['max_tokens']:.0f}")
        else:
            print(f"  ✅ 모든 청크가 토큰 제한 준수")
        
        # 결과 출력
        print("\n" + "=" * 80)
        print("검증 결과")
        print("=" * 80)
        
        print(f"\n📊 기본 통계:")
        print(f"  - 총 문서: {self.stats['total_documents']:,}개")
        print(f"  - 총 청크: {self.stats['total_chunks']:,}개")
        
        # RAG 최적화 통계
        optimal = self.stats.get('optimal_chunks', 0)
        too_short = self.stats.get('suboptimal_too_short', 0)
        too_long = self.stats.get('suboptimal_too_long', 0)
        total_checked = optimal + too_short + too_long
        
        if total_checked > 0:
            print(f"\n🎯 RAG 최적화 분석 (100-2000자 기준):")
            print(f"  - 최적 범위: {optimal:,}개 ({optimal/total_checked*100:.1f}%)")
            print(f"  - 너무 짧음: {too_short:,}개 ({too_short/total_checked*100:.1f}%)")
            print(f"  - 너무 김: {too_long:,}개 ({too_long/total_checked*100:.1f}%)")
        
        # 청크 타입별 문제 통계
        print(f"\n📝 청크 타입별 문제 요약:")
        type_issues = {}
        for key in self.stats:
            if key.startswith('too_short_') or key.startswith('too_long_'):
                parts = key.split('_', 2)
                issue_type = parts[0] + '_' + parts[1]
                chunk_type = parts[2] if len(parts) > 2 else 'unknown'
                
                if chunk_type not in type_issues:
                    type_issues[chunk_type] = {'too_short': 0, 'too_long': 0}
                
                if issue_type == 'too_short':
                    type_issues[chunk_type]['too_short'] = self.stats[key]
                elif issue_type == 'too_long':
                    type_issues[chunk_type]['too_long'] = self.stats[key]
        
        for chunk_type, issues in sorted(type_issues.items()):
            rules = CHUNK_PROCESSING_RULES.get(chunk_type, CHUNK_PROCESSING_RULES['default'])
            desc = rules['description']
            if issues['too_short'] > 0 or issues['too_long'] > 0:
                print(f"  - {desc} ({chunk_type}):")
                if issues['too_short'] > 0:
                    print(f"    • 너무 짧음: {issues['too_short']:,}개")
                if issues['too_long'] > 0:
                    print(f"    • 너무 김: {issues['too_long']:,}개")
        
        print(f"\n🔍 이슈:")
        print(f"  - ❌ Critical 오류: {len(self.issues)}개")
        print(f"  - ⚠️  경고: {len(self.warnings)}개")
        
        if self.issues:
            print(f"\n❌ Critical 오류 목록 (상위 10개):")
            for issue in self.issues[:10]:
                print(f"  {issue}")
            if len(self.issues) > 10:
                print(f"  ... 외 {len(self.issues) - 10}개")
        
        if self.warnings:
            print(f"\n⚠️  경고 목록 (상위 5개):")
            for warning in self.warnings[:5]:
                print(f"  {warning}")
            if len(self.warnings) > 5:
                print(f"  ... 외 {len(self.warnings) - 5}개")
        
        # 개선 권장사항
        if too_short > total_checked * 0.1:  # 10% 이상이 너무 짧은 경우
            print(f"\n💡 개선 권장사항:")
            print(f"  - 짧은 청크 병합을 권장합니다 (data_transform_pipeline.py 수정)")
        
        if too_long > total_checked * 0.05:  # 5% 이상이 너무 긴 경우
            print(f"  - 긴 청크 분할을 권장합니다 (data_transform_pipeline.py 수정)")
        
        print("\n" + "=" * 80)
        if all_valid and not self.issues:
            print("✅ 검증 통과! 임베딩 진행 가능합니다.")
            if self.warnings:
                print("   (경고 사항이 있으나 치명적이지 않음)")
        else:
            print("❌ 검증 실패! Critical 오류를 수정한 후 다시 시도하세요.")
        print("=" * 80)
        
        return all_valid, dict(self.stats)
    
    def show_sample_data(self, data: Dict[str, Dict], n: int = 2):
        """샘플 데이터 출력"""
        print("\n" + "=" * 80)
        print("샘플 데이터 미리보기")
        print("=" * 80)
        
        for file_name, file_data in data.items():
            documents = file_data.get('documents', [])[:n]
            
            for doc in documents:
                print(f"\n📄 [{doc['doc_type']}] {doc['doc_id']}")
                print(f"  제목: {doc['title']}")
                print(f"  출처: {doc['source_org']}")
                print(f"  청크 수: {len(doc['chunks'])}개")
                
                # 첫 번째 청크 미리보기
                if doc['chunks']:
                    chunk = doc['chunks'][0]
                    print(f"\n  [청크 0] {chunk['chunk_id']}")
                    print(f"    타입: {chunk['chunk_type']}")
                    print(f"    인덱스: {chunk['chunk_index']}/{chunk['chunk_total']}")
                    print(f"    길이: {chunk['content_length']}자")
                    print(f"    drop: {chunk['drop']}")
                    content_preview = chunk['content'][:200].replace('\n', ' ')
                    print(f"    내용: {content_preview}...")

def main():
    """메인 함수"""
    validator = TransformedDataValidator()
    
    # 1. 데이터 로드
    print("=" * 80)
    print("변환된 데이터 로드")
    print("=" * 80)
    data = validator.load_all_data()
    
    if not data:
        print("\n❌ 로드할 데이터가 없습니다.")
        print("먼저 data_transform_pipeline.py를 실행하세요.")
        return
    
    print(f"\n✅ {len(data)}개 파일 로드 완료")
    
    # 2. 샘플 데이터 미리보기
    validator.show_sample_data(data, n=1)
    
    # 3. 검증
    all_valid, stats = validator.validate_all(data)
    
    # 4. 결과 저장
    result = {
        'valid': all_valid and not validator.issues,
        'issues_count': len(validator.issues),
        'warnings_count': len(validator.warnings),
        'issues': validator.issues,
        'warnings': validator.warnings,
        'stats': stats
    }
    
    output_path = validator.data_dir / 'validation_result.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 검증 결과 저장: {output_path}")
    
    return 0 if result['valid'] else 1

if __name__ == '__main__':
    exit(main())
