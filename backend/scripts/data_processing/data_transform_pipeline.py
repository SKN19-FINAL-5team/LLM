#!/usr/bin/env python3
"""
데이터 변환 파이프라인

원본 JSONL 데이터를 PostgreSQL 스키마에 맞게 변환하여:
1. JSON 파일로 저장 (검토용)
2. PostgreSQL에 삽입

Features:
- 모든 chunk_index를 0-based로 통일
- 변환 전후 검증
- 진행 상황 저장 (중단 시 재개 가능)
- 상세한 로그
"""

import json
import os
import glob
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

# 현재 디렉토리를 sys.path에 추가하여 metadata_enricher import 가능하도록
import sys
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from metadata_enricher import MetadataEnricher

load_dotenv()

# 스크립트 위치 기준으로 프로젝트 루트 찾기
SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/data_processing/
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # ddoksori_demo/
DATA_DIR = PROJECT_ROOT / "backend" / "data"

# 청크 타입별 처리 규칙 (개선됨 - 타입별 최적 길이 차별화)
# 토큰 제한: KURE-v1 모델 512 토큰 = 약 768-1024자
# 안전 범위: 타입에 따라 400-800자로 차별화
CHUNK_PROCESSING_RULES = {
    'decision': {
        'min_length': 100,
        'max_length': 600,  # 개선: 간결한 결정문에 최적화 (700 → 600)
        'target_length': 500,  # 개선: 목표 크기 축소 (600 → 500)
        'merge_allowed': False,  # 결정문은 독립성 유지
        'split_allowed': True,
        'overlap_size': 100,
        'overlap_mode': 'sentence',  # 신규: 문장 단위 중첩
        'drop_if_empty': True,
        'description': '주문(결정) - 간결한 결정문'
    },
    'reasoning': {
        'min_length': 150,
        'max_length': 800,  # 개선: 상세한 논리 전개 허용 (700 → 800)
        'target_length': 700,  # 개선: 목표 크기 증가 (600 → 700)
        'merge_allowed': True,
        'split_allowed': True,
        'overlap_size': 150,
        'overlap_mode': 'sentence',
        'description': '이유(근거) - 상세한 논리 전개'
    },
    'judgment': {
        'min_length': 150,
        'max_length': 800,  # 개선: 판단 내용에 충분한 공간 (700 → 800)
        'target_length': 700,  # 개선: 목표 크기 증가 (600 → 700)
        'merge_allowed': True,
        'split_allowed': True,
        'overlap_size': 150,
        'overlap_mode': 'sentence',
        'description': '판단 - 법적 근거와 판단'
    },
    'parties_claim': {
        'min_length': 150,
        'max_length': 750,  # 개선: 당사자 주장에 적절한 길이
        'target_length': 650,
        'merge_allowed': True,
        'split_allowed': True,
        'overlap_size': 150,
        'overlap_mode': 'sentence',
        'description': '당사자 주장 - 기초사실'
    },
    'law': {
        'min_length': 50,
        'max_length': 500,  # 개선: 조문 단위로 짧게 유지 (700 → 500)
        'target_length': 400,  # 개선: 목표 크기 축소 (600 → 400)
        'merge_allowed': False,
        'split_allowed': True,
        'overlap_size': 80,  # 개선: 중첩 크기 축소 (100 → 80)
        'overlap_mode': 'sentence',
        'drop_if_empty': True,
        'enrich_with_metadata': True,
        'description': '법령 조문'
    },
    'law_reference': {
        'min_length': 50,
        'max_length': 500,  # 개선: 법령 참조는 간결하게 (700 → 500)
        'target_length': 400,
        'merge_allowed': False,
        'split_allowed': True,
        'overlap_size': 80,
        'overlap_mode': 'sentence',
        'drop_if_empty': True,
        'description': '법령 참조'
    },
    'resolution_row': {
        'min_length': 100,
        'max_length': 700,
        'target_length': 600,
        'merge_allowed': False,
        'split_allowed': True,
        'overlap_size': 100,
        'overlap_mode': 'sentence',
        'description': '소비자분쟁해결기준 행'
    },
    'qa_combined': {
        'min_length': 150,
        'max_length': 700,
        'target_length': 600,
        'merge_allowed': False,  # Q&A 쌍은 독립성 유지
        'split_allowed': True,
        'overlap_size': 100,
        'overlap_mode': 'sentence',
        'description': '질의응답 통합'
    },
    'article': {
        'min_length': 100,
        'max_length': 500,  # 개선: 조문은 짧게 (700 → 500)
        'target_length': 400,
        'merge_allowed': False,
        'split_allowed': True,
        'overlap_size': 80,
        'overlap_mode': 'sentence',
        'description': '조문'
    },
    'paragraph': {
        'min_length': 100,
        'max_length': 600,  # 개선: 항 단위 (700 → 600)
        'target_length': 500,
        'merge_allowed': True,
        'split_allowed': True,
        'overlap_size': 100,
        'overlap_mode': 'sentence',
        'description': '항'
    },
    # 기본 규칙
    'default': {
        'min_length': 100,
        'max_length': 700,
        'target_length': 600,
        'merge_allowed': True,
        'split_allowed': True,
        'overlap_size': 100,
        'overlap_mode': 'sentence',
        'drop_if_empty': True,
        'description': '기본 규칙'
    }
}

class DataTransformer:
    """데이터 변환 파이프라인"""
    
    def __init__(self, output_dir: Path = None, use_db: bool = False, enrich_metadata: bool = True):
        """
        Args:
            output_dir: 변환된 데이터를 저장할 디렉토리 (None이면 자동 설정)
            use_db: DB에 삽입할지 여부
            enrich_metadata: 메타데이터 보강 여부
        """
        if output_dir is None:
            output_dir = DATA_DIR / "transformed"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.use_db = use_db
        self.conn = None
        self.cur = None
        
        if use_db:
            self._connect_db()
        
        self.enrich_metadata = enrich_metadata
        if enrich_metadata:
            self.metadata_enricher = MetadataEnricher()
            print("✅ 메타데이터 보강 활성화")
        else:
            self.metadata_enricher = None
        
        self.stats = {
            'documents': 0,
            'chunks': 0,
            'skipped': 0,
            'errors': [],
            'enriched_chunks': 0
        }
    
    def _connect_db(self):
        """데이터베이스 연결"""
        self.conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        self.cur = self.conn.cursor()
        print("✅ 데이터베이스 연결 성공")
    
    def _assign_chunk_indices(self, chunks: List[Dict]) -> List[Dict]:
        """
        청크 리스트에 0-based 인덱스 할당
        
        ⚠️ 중요: 원본 데이터의 인덱스는 무시하고 새로 할당
        """
        total = len(chunks)
        for idx, chunk in enumerate(chunks):
            chunk['chunk_index'] = idx  # 0, 1, 2, ...
            chunk['chunk_total'] = total
        return chunks
    
    def _get_chunk_rules(self, chunk_type: str) -> Dict:
        """청크 타입에 따른 처리 규칙 반환"""
        return CHUNK_PROCESSING_RULES.get(chunk_type, CHUNK_PROCESSING_RULES['default'])
    
    def _estimate_token_count(self, text: str) -> int:
        """
        한국어 텍스트의 토큰 수 추정
        
        한국어 토큰 변환율: 약 1.5-2자 = 1토큰
        보수적 추정: 1.5자 = 1토큰
        
        Args:
            text: 토큰 수를 추정할 텍스트
            
        Returns:
            추정된 토큰 수
        """
        char_count = len(text)
        return int(char_count / 1.5)
    
    def _validate_token_limit(self, chunks: List[Dict], max_tokens: int = 512) -> Dict:
        """
        모든 청크의 토큰 수 검증
        
        Args:
            chunks: 검증할 청크 리스트
            max_tokens: 최대 토큰 수 (기본: 512)
            
        Returns:
            {
                'valid': bool,
                'violations': List[Dict],
                'stats': Dict
            }
        """
        violations = []
        token_counts = []
        
        for chunk in chunks:
            if chunk.get('drop', False):
                continue
            
            content = chunk.get('content', '')
            estimated_tokens = self._estimate_token_count(content)
            token_counts.append(estimated_tokens)
            
            if estimated_tokens > max_tokens:
                violations.append({
                    'chunk_id': chunk.get('chunk_id'),
                    'chunk_type': chunk.get('chunk_type'),
                    'char_count': len(content),
                    'estimated_tokens': estimated_tokens,
                    'excess_tokens': estimated_tokens - max_tokens
                })
        
        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'stats': {
                'total_chunks': len([c for c in chunks if not c.get('drop', False)]),
                'avg_tokens': sum(token_counts) / len(token_counts) if token_counts else 0,
                'max_tokens': max(token_counts) if token_counts else 0,
                'violation_count': len(violations),
                'violation_rate': len(violations) / len(token_counts) if token_counts else 0
            }
        }
    
    def _group_sentences(self, sentences: List[str], target_size: int) -> List[str]:
        """
        문장들을 목표 크기에 맞게 그룹화
        
        Args:
            sentences: 문장 리스트 (구분자 포함)
            target_size: 목표 크기
            
        Returns:
            그룹화된 문장 리스트
        """
        grouped = []
        current_group = []
        current_length = 0
        
        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            sentence_length = len(sentence)
            
            if current_length + sentence_length > target_size and current_group:
                # 현재 그룹을 저장
                grouped.append(''.join(current_group))
                current_group = []
                current_length = 0
            
            current_group.append(sentence)
            current_length += sentence_length
            i += 1
        
        # 남은 그룹 처리
        if current_group:
            grouped.append(''.join(current_group))
        
        return grouped
    
    def _split_chunk_semantic(self, chunk: Dict, rules: Dict) -> List[Dict]:
        """
        의미 단위 기반 청크 분할 (개선)
        
        분할 우선순위:
        1. 이중 줄바꿈 (문단 구분)
        2. 문장 구분 (마침표, 물음표, 느낌표)
        3. 쉼표/세미콜론
        
        Args:
            chunk: 분할할 청크
            rules: 처리 규칙
            
        Returns:
            분할된 청크 리스트
        """
        import re
        
        content = chunk.get('content', '')
        target_size = rules.get('target_length', 600)
        max_size = rules.get('max_length', 700)
        
        # 1순위: 문단 단위 분할
        sections = re.split(r'\n\n+', content)
        
        # 2순위: 너무 긴 문단은 문장 단위로 추가 분할
        refined_sections = []
        for section in sections:
            if len(section) > max_size:
                # 문장 구분자로 분할 (구분자도 포함)
                sentences = re.split(r'([.!?]\s+)', section)
                grouped = self._group_sentences(sentences, target_size)
                refined_sections.extend(grouped)
            else:
                refined_sections.append(section)
        
        # 목표 크기에 맞게 재조합 (다음 메서드에서 구현)
        return self._regroup_sections(chunk, refined_sections, rules)
    
    def _extract_sentences(self, text: str) -> List[str]:
        """
        텍스트를 문장 단위로 분리 (개선됨)
        
        Args:
            text: 분리할 텍스트
            
        Returns:
            문장 리스트
        """
        import re
        
        # 문장 구분자로 분할 (구분자 포함)
        # 마침표, 물음표, 느낌표 + 공백/줄바꿈
        parts = re.split(r'([.!?](?:\s+|\n+))', text)
        
        # 구분자를 문장에 다시 붙이기
        sentences = []
        for i in range(0, len(parts)-1, 2):
            if i+1 < len(parts):
                sentence = parts[i] + parts[i+1]
                sentences.append(sentence.strip())
        
        # 마지막 부분 처리 (구분자가 없는 경우)
        if len(parts) % 2 == 1 and parts[-1].strip():
            sentences.append(parts[-1].strip())
        
        return [s for s in sentences if s]
    
    def _get_sentence_overlap(self, sentences: List[str], overlap_size: int) -> str:
        """
        문장 단위로 overlap 텍스트 생성 (개선됨)
        
        Args:
            sentences: 문장 리스트
            overlap_size: 목표 overlap 크기 (문자 수)
            
        Returns:
            overlap 텍스트
        """
        if not sentences:
            return ""
        
        # 뒤에서부터 문장을 추가하면서 overlap_size에 근접하게
        overlap_sentences = []
        current_length = 0
        
        for sentence in reversed(sentences):
            sentence_length = len(sentence)
            if current_length + sentence_length > overlap_size and overlap_sentences:
                break
            overlap_sentences.insert(0, sentence)
            current_length += sentence_length
        
        return ' '.join(overlap_sentences)
    
    def _validate_chunk_quality(self, content: str) -> tuple[bool, str]:
        """
        청크 품질 검증 (신규)
        
        검증 항목:
        1. 문장 완결성 (마지막 문장이 완결되었는지)
        2. 최소 길이 충족
        3. 특수문자만으로 구성되지 않았는지
        
        Args:
            content: 청크 내용
            
        Returns:
            (is_valid, reason): 유효 여부와 이유
        """
        if not content or not content.strip():
            return False, "빈 내용"
        
        content = content.strip()
        
        # 1. 최소 길이 체크 (20자 이상)
        if len(content) < 20:
            return False, f"내용이 너무 짧음 ({len(content)}자)"
        
        # 2. 특수문자만으로 구성되지 않았는지
        import re
        text_only = re.sub(r'[^가-힣a-zA-Z0-9]', '', content)
        if len(text_only) < 10:
            return False, "의미 있는 텍스트 부족"
        
        # 3. 문장 완결성 체크 (마지막이 문장 종결 부호로 끝나는지)
        last_char = content[-1]
        sentence_enders = ['.', '!', '?', '다', '요', '음', '니', '지', '까', '나']
        
        # 마지막이 종결 부호가 아니면 경고 (but valid)
        if last_char not in sentence_enders:
            # 이건 경고만 하고 통과
            pass
        
        return True, ""
    
    def _regroup_sections(self, chunk: Dict, sections: List[str], rules: Dict) -> List[Dict]:
        """
        섹션들을 목표 크기에 맞게 재조합하며 Overlapping 적용 (개선됨)
        
        개선사항:
        - 문장 단위 Overlapping
        - 청크 품질 검증
        
        Args:
            chunk: 원본 청크
            sections: 분할된 섹션 리스트
            rules: 처리 규칙
            
        Returns:
            재조합된 청크 리스트 (overlap 적용)
        """
        target_size = rules.get('target_length', 600)
        max_size = rules.get('max_length', 700)
        overlap_size = rules.get('overlap_size', 150)
        overlap_mode = rules.get('overlap_mode', 'char')  # 'char' or 'sentence'
        
        sub_chunks = []
        current_buffer = []
        current_length = 0
        previous_sentences = []  # 이전 청크의 문장들 (sentence mode용)
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            section_length = len(section)
            
            # 버퍼가 목표 크기 근처에 도달하면 청크 생성
            if current_length + section_length > target_size and current_buffer:
                # 현재 버퍼로 청크 생성
                chunk_content = '\n\n'.join(current_buffer)
                
                # Overlapping 적용
                if previous_sentences and sub_chunks:
                    if overlap_mode == 'sentence':
                        # 문장 단위 overlap (개선됨)
                        overlap_text = self._get_sentence_overlap(previous_sentences, overlap_size)
                        if overlap_text:
                            chunk_content = overlap_text + '\n\n' + chunk_content
                    else:
                        # 기존 문자 단위 overlap
                        overlap_text = chunk_content[:overlap_size] if len(chunk_content) > overlap_size else chunk_content
                        if overlap_text:
                            chunk_content = overlap_text + '\n\n' + chunk_content
                
                # 품질 검증 (신규)
                is_valid, reason = self._validate_chunk_quality(chunk_content)
                if not is_valid:
                    # 품질이 낮으면 경고만 하고 계속 진행
                    # (drop하지 않음 - 데이터 손실 방지)
                    if not chunk.get('metadata'):
                        chunk['metadata'] = {}
                    chunk['metadata']['quality_warning'] = reason
                
                sub_chunks.append({
                    **chunk,
                    'content': chunk_content,
                    'content_length': len(chunk_content),
                    'chunk_id': f"{chunk['chunk_id']}_part{len(sub_chunks)+1}",
                    'parent_chunk_id': chunk.get('chunk_id'),
                    'metadata': {
                        **chunk.get('metadata', {}),
                        'is_split': True,
                        'part_number': len(sub_chunks) + 1
                    }
                })
                
                # 다음 overlap을 위해 현재 청크의 문장 저장
                previous_sentences = self._extract_sentences(chunk_content)
                
                # 버퍼 초기화
                current_buffer = []
                current_length = 0
            
            current_buffer.append(section)
            current_length += section_length + 2  # \n\n 고려
        
        # 남은 버퍼 처리
        if current_buffer:
            chunk_content = '\n\n'.join(current_buffer)
            if previous_sentences and sub_chunks:
                if overlap_mode == 'sentence':
                    overlap_text = self._get_sentence_overlap(previous_sentences, overlap_size)
                    if overlap_text:
                        chunk_content = overlap_text + '\n\n' + chunk_content
                else:
                    overlap_text = chunk_content[:overlap_size] if len(chunk_content) > overlap_size else chunk_content
                    if overlap_text:
                        chunk_content = overlap_text + '\n\n' + chunk_content
            
            # 품질 검증
            is_valid, reason = self._validate_chunk_quality(chunk_content)
            if not is_valid:
                if not chunk.get('metadata'):
                    chunk['metadata'] = {}
                chunk['metadata']['quality_warning'] = reason
            
            sub_chunks.append({
                **chunk,
                'content': chunk_content,
                'content_length': len(chunk_content),
                'chunk_id': f"{chunk['chunk_id']}_part{len(sub_chunks)+1}" if sub_chunks else chunk['chunk_id'],
                'parent_chunk_id': chunk.get('chunk_id') if sub_chunks else None,
                'metadata': {
                    **chunk.get('metadata', {}),
                    'is_split': True if sub_chunks else False,
                    'part_number': len(sub_chunks) + 1 if sub_chunks else 1
                }
            })
        
        return sub_chunks if sub_chunks else [chunk]
    
    def _merge_short_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        짧은 청크를 이전/다음 청크와 병합
        
        Args:
            chunks: 청크 리스트
            
        Returns:
            병합된 청크 리스트
        """
        if not chunks:
            return chunks
        
        merged = []
        buffer = []
        
        for i, chunk in enumerate(chunks):
            content = chunk.get('content', '')
            chunk_type = chunk.get('chunk_type', 'default')
            rules = self._get_chunk_rules(chunk_type)
            
            # drop=True인 청크는 그대로 유지
            if chunk.get('drop', False):
                if buffer:
                    # 버퍼에 있던 청크들을 마지막 merged 청크와 병합
                    if merged:
                        last_chunk = merged[-1]
                        buffer_content = "\n\n".join([c['content'] for c in buffer])
                        last_chunk['content'] = last_chunk['content'] + "\n\n" + buffer_content
                        last_chunk['content_length'] = len(last_chunk['content'])
                    else:
                        # merged가 비어있으면 버퍼 청크들을 추가
                        merged.extend(buffer)
                    buffer = []
                merged.append(chunk)
                continue
            
            # 병합이 허용되지 않는 타입이거나 최소 길이를 충족하는 청크
            if not rules['merge_allowed'] or len(content) >= rules['min_length']:
                # 버퍼가 있으면 현재 청크와 병합
                if buffer:
                    merged_content = "\n\n".join([c['content'] for c in buffer] + [content])
                    chunk['content'] = merged_content
                    chunk['content_length'] = len(merged_content)
                    buffer = []
                merged.append(chunk)
            else:
                # 짧은 청크를 버퍼에 추가
                buffer.append(chunk)
        
        # 남은 버퍼 처리
        if buffer:
            if merged:
                # 마지막 청크와 병합
                last_chunk = merged[-1]
                buffer_content = "\n\n".join([c['content'] for c in buffer])
                last_chunk['content'] = last_chunk['content'] + "\n\n" + buffer_content
                last_chunk['content_length'] = len(last_chunk['content'])
            else:
                # merged가 비어있으면 버퍼 청크들을 그대로 추가
                merged.extend(buffer)
        
        return merged
    
    def _split_long_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        긴 청크를 의미 단위로 분할 (개선된 로직 사용)
        
        Args:
            chunks: 청크 리스트
            
        Returns:
            분할된 청크 리스트
        """
        result = []
        
        for chunk in chunks:
            content = chunk.get('content', '')
            chunk_type = chunk.get('chunk_type', 'default')
            rules = self._get_chunk_rules(chunk_type)
            
            # drop=True인 청크는 그대로 유지
            if chunk.get('drop', False):
                result.append(chunk)
                continue
            
            # 분할이 허용되지 않거나 최대 길이 이하인 청크
            if not rules.get('split_allowed', False) or len(content) <= rules.get('max_length', 700):
                result.append(chunk)
                continue
            
            # 개선된 의미 단위 분할 사용
            sub_chunks = self._split_chunk_semantic(chunk, rules)
            result.extend(sub_chunks)
        
        return result
    
    def _optimize_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        청크 최적화 (병합 + 분할 + 검증)
        
        Args:
            chunks: 청크 리스트
            
        Returns:
            최적화된 청크 리스트
        """
        # 1. 짧은 청크 병합
        chunks = self._merge_short_chunks(chunks)
        
        # 2. 긴 청크 분할 (개선된 로직)
        chunks = self._split_long_chunks(chunks)
        
        # 3. 빈 청크 처리
        for chunk in chunks:
            content = chunk.get('content', '').strip()
            chunk_type = chunk.get('chunk_type', 'default')
            rules = self._get_chunk_rules(chunk_type)
            
            # 빈 청크이고 drop_if_empty가 True인 경우
            if not content and rules.get('drop_if_empty', False):
                chunk['drop'] = True
        
        # 4. 토큰 제한 검증
        validation_result = self._validate_token_limit(chunks)
        
        if not validation_result['valid']:
            print(f"  ⚠️  토큰 제한 초과 청크: {validation_result['stats']['violation_count']}개")
            print(f"  ⚠️  초과율: {validation_result['stats']['violation_rate']*100:.1f}%")
            
            # 초과 청크 재분할 (더 작은 크기로)
            chunks = self._resplit_violations(chunks, validation_result['violations'])
            
            # 재검증
            revalidation = self._validate_token_limit(chunks)
            if revalidation['valid']:
                print(f"  ✅ 재분할 완료: 토큰 제한 준수")
            else:
                print(f"  ⚠️  재분할 후에도 {revalidation['stats']['violation_count']}개 초과")
        
        return chunks
    
    def _resplit_violations(self, chunks: List[Dict], violations: List[Dict]) -> List[Dict]:
        """
        토큰 제한 초과 청크를 재분할
        
        Args:
            chunks: 청크 리스트
            violations: 위반 사항 리스트
            
        Returns:
            재분할된 청크 리스트
        """
        violation_ids = {v['chunk_id'] for v in violations}
        result = []
        
        for chunk in chunks:
            if chunk['chunk_id'] in violation_ids:
                # 더 작은 크기로 재분할 (target_length를 50% 줄임)
                rules = self._get_chunk_rules(chunk.get('chunk_type', 'default'))
                adjusted_rules = {
                    **rules, 
                    'target_length': rules.get('target_length', 600) // 2,
                    'max_length': rules.get('max_length', 700) // 2
                }
                sub_chunks = self._split_chunk_semantic(chunk, adjusted_rules)
                result.extend(sub_chunks)
            else:
                result.append(chunk)
        
        return result
    
    def _validate_chunk_indices(self, doc_id: str, chunks: List[Dict]):
        """chunk_index 검증"""
        chunks_sorted = sorted(chunks, key=lambda x: x['chunk_index'])
        
        expected_indices = list(range(len(chunks)))
        actual_indices = [c['chunk_index'] for c in chunks_sorted]
        
        if expected_indices != actual_indices:
            raise ValueError(
                f"❌ Invalid chunk_index for {doc_id}:\n"
                f"   Expected: {expected_indices}\n"
                f"   Actual: {actual_indices}"
            )
        
        for chunk in chunks:
            if chunk['chunk_total'] != len(chunks):
                raise ValueError(
                    f"❌ Invalid chunk_total for {chunk.get('chunk_id', 'unknown')}:\n"
                    f"   Expected: {len(chunks)}\n"
                    f"   Actual: {chunk['chunk_total']}"
                )
            
            if chunk['chunk_index'] >= chunk['chunk_total']:
                raise ValueError(
                    f"❌ chunk_index >= chunk_total for {chunk.get('chunk_id', 'unknown')}:\n"
                    f"   chunk_index: {chunk['chunk_index']}\n"
                    f"   chunk_total: {chunk['chunk_total']}"
                )
    
    def _enrich_document(self, doc_data: Dict) -> Dict:
        """문서의 모든 청크에 메타데이터 보강 적용"""
        if not self.enrich_metadata or not self.metadata_enricher:
            return doc_data
        
        enriched_count = 0
        for chunk in doc_data.get('chunks', []):
            # drop=True인 청크는 스킵
            if chunk.get('drop', False):
                continue
            
            # 메타데이터 보강
            self.metadata_enricher.enrich_chunk_metadata(chunk, extract_all=True)
            enriched_count += 1
        
        self.stats['enriched_chunks'] += enriched_count
        return doc_data
    
    def _save_json(self, data: Dict, filename: str):
        """변환된 데이터를 JSON 파일로 저장"""
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  💾 저장: {output_path}")
    
    def transform_law_data(self, file_path: str) -> Dict:
        """
        법령 데이터 변환
        - 문서 단위: 법령별 (law_id)
        - 청크 단위: 조문/항/호/목별 (unit_id)
        """
        print(f"\n📜 법령 데이터 변환: {file_path}")
        
        chunks_by_law = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                law_id = data['law_id']
                
                if law_id not in chunks_by_law:
                    chunks_by_law[law_id] = {
                        'doc_id': f"statute:{law_id}",
                        'doc_type': 'law',
                        'title': data['law_name'],
                        'source_org': 'statute',
                        'category_path': None,
                        'url': None,
                        'metadata': {'law_id': law_id},
                        'chunks': []
                    }
                
                # 청크 생성
                chunk = {
                    'chunk_id': f"statute:{law_id}:{data['unit_id']}",
                    'chunk_type': data['unit_level'],
                    'content': f"[법령] {data['law_name']}\n[조문] {data['path']}\n\n{data['index_text']}",
                    'content_length': len(data['index_text']),
                    'drop': False,
                    'metadata': {
                        'unit_id': data['unit_id'],
                        'path': data['path'],
                        'article_no': data.get('article_no'),
                        'paragraph_no': data.get('paragraph_no')
                    }
                }
                chunks_by_law[law_id]['chunks'].append(chunk)
        
        # 각 법령별로 청크 최적화 후 0-based 인덱스 할당
        result = {'documents': []}
        
        for law_id, doc_data in chunks_by_law.items():
            # 청크 최적화
            doc_data['chunks'] = self._optimize_chunks(doc_data['chunks'])
            
            # 0-based 인덱스 할당
            doc_data['chunks'] = self._assign_chunk_indices(doc_data['chunks'])
            self._validate_chunk_indices(doc_data['doc_id'], doc_data['chunks'])
            
            # 메타데이터 보강
            doc_data = self._enrich_document(doc_data)
            
            result['documents'].append(doc_data)
            
            self.stats['documents'] += 1
            self.stats['chunks'] += len(doc_data['chunks'])
            
            print(f"  ✅ {doc_data['title']}: {len(doc_data['chunks'])}개 청크 (최적화 완료)")
        
        return result
    
    def transform_law_single_file(self, file_path: str) -> Dict:
        """
        단일 법령 JSONL 파일을 PostgreSQL 형식으로 변환
        (여러 법령이 하나의 파일에 있을 수 있음)
        
        Args:
            file_path: 법령 JSONL 파일 경로
        
        Returns:
            {
                'documents': [...]
            }
        """
        from pathlib import Path
        
        file_name = Path(file_path).stem  # 예: "Consumer_Basic_Law_chunks"
        print(f"\n📜 법령 파일 변환: {file_name}")
        
        # 법령명 매핑 (파일명 -> 한글명)
        law_name_map = {
            'Civil_Law_chunks': '민법',
            'Commercial_Law_chunks': '상법',
            'Consumer_Basic_Law_chunks': '소비자기본법',
            'E_Commerce_Consumer_Law_chunks': '전자상거래소비자보호법',
            'Product_Liability_Law_chunks': '제조물책임법',
            'Terms_Regulation_Law_chunks': '약관규제법',
            'Installment_Sales_Law_chunks': '할부거래법',
            'Direct_Sales_Law_chunks': '방문판매법',
            'Fair_Ads_Law_chunks': '표시광고법',
            'Content_Industry_Promotion_Law_chunks': '콘텐츠산업진흥법',
            'E_Transaction_Law_chunks': '전자거래법'
        }
        
        # 파일에서 law_id별로 그룹화
        chunks_by_law = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                    
                data = json.loads(line)
                law_id = data['law_id']
                law_name = data['law_name']
                
                if law_id not in chunks_by_law:
                    # doc_id를 파일명 기반으로 생성 (law_id 대신)
                    doc_id = f"law:{file_name.lower()}"
                    
                    chunks_by_law[law_id] = {
                        'doc_id': doc_id,
                        'doc_type': 'law',
                        'title': law_name,
                        'source_org': 'statute',
                        'category_path': ['법령', law_name],
                        'url': None,
                        'collected_at': None,
                        'metadata': {
                            'law_id': law_id,
                            'law_name': law_name,
                            'file_name': file_name
                        },
                        'chunks': []
                    }
                
                # 청크 생성
                chunk = {
                    'chunk_id': f"law:{file_name.lower()}::{data['unit_id']}",
                    'chunk_type': data['unit_level'],
                    'content': f"[법령] {law_name}\n[조문] {data['path']}\n\n{data['index_text']}",
                    'content_length': len(data['index_text']),
                    'drop': False,
                    'metadata': {
                        'unit_id': data['unit_id'],
                        'path': data['path'],
                        'article_no': data.get('article_no'),
                        'paragraph_no': data.get('paragraph_no')
                    }
                }
                chunks_by_law[law_id]['chunks'].append(chunk)
        
        # 각 법령별로 청크 최적화 후 0-based 인덱스 할당
        result = {'documents': []}
        
        for law_id, doc_data in chunks_by_law.items():
            # 청크 최적화
            doc_data['chunks'] = self._optimize_chunks(doc_data['chunks'])
            
            # 0-based 인덱스 할당
            doc_data['chunks'] = self._assign_chunk_indices(doc_data['chunks'])
            self._validate_chunk_indices(doc_data['doc_id'], doc_data['chunks'])
            
            # 메타데이터 보강
            doc_data = self._enrich_document(doc_data)
            
            result['documents'].append(doc_data)
            
            self.stats['documents'] += 1
            self.stats['chunks'] += len(doc_data['chunks'])
            
            print(f"  ✅ {doc_data['title']}: {len(doc_data['chunks'])}개 청크")
        
        return result
    
    def transform_criteria_table1(self, file_path: str) -> Dict:
        """
        기준 데이터 변환 - table1 (품목 분류)
        - 문서 단위: 전체 테이블 하나
        - 청크 단위: 각 품목
        """
        print(f"\n📋 기준 데이터 변환 (table1 - 품목): {file_path}")
        
        doc_id = 'criteria:table1'
        chunks = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                    
                data = json.loads(line)
                
                # embed_text를 content로 사용
                content = data.get('embed_text', '')
                metadata_raw = data.get('metadata', {})
                
                # stable_id를 chunk_id로 사용
                chunk_id = data.get('stable_id', f"{doc_id}::item{len(chunks):04d}")
                
                chunk = {
                    'chunk_id': chunk_id,
                    'chunk_type': 'item',
                    'content': content,
                    'content_length': len(content),
                    'drop': False,
                    'metadata': {
                        'item_name': metadata_raw.get('item_name', ''),
                        'category': metadata_raw.get('category', ''),
                        'industry': metadata_raw.get('industry', ''),
                        'item_group': metadata_raw.get('item_group', ''),
                        'aliases': metadata_raw.get('aliases', [])
                    }
                }
                chunks.append(chunk)
        
        # 문서 메타데이터
        document = {
            'doc_id': doc_id,
            'doc_type': 'criteria_item_list',
            'title': '소비자분쟁해결기준 - 대상품목',
            'source_org': 'KCA',
            'category_path': ['기준', '품목분류'],
            'url': None,
            'collected_at': None,
            'metadata': {
                'table_type': 'table1',
                'item_count': len(chunks)
            },
            'chunks': []
        }
        
        # 청크 최적화 및 인덱스 할당
        document['chunks'] = self._optimize_chunks(chunks)
        document['chunks'] = self._assign_chunk_indices(document['chunks'])
        self._validate_chunk_indices(document['doc_id'], document['chunks'])
        
        # 메타데이터 보강
        document = self._enrich_document(document)
        
        self.stats['documents'] += 1
        self.stats['chunks'] += len(document['chunks'])
        
        print(f"  ✅ {len(document['chunks'])}개 품목 청크")
        
        return {'documents': [document]}
    
    def transform_criteria_table3(self, file_path: str) -> Dict:
        """
        기준 데이터 변환 - table3 (품질보증기간)
        - 문서 단위: 전체 테이블 하나
        - 청크 단위: 각 품목별 보증기간
        """
        print(f"\n📋 기준 데이터 변환 (table3 - 품질보증기간): {file_path}")
        
        doc_id = 'criteria:table3'
        chunks = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                    
                data = json.loads(line)
                
                # embed_text를 content로 사용
                content = data.get('embed_text', '')
                metadata_raw = data.get('metadata', {})
                
                # stable_id를 chunk_id로 사용
                chunk_id = data.get('stable_id', f"{doc_id}::warranty{len(chunks):04d}")
                
                chunk = {
                    'chunk_id': chunk_id,
                    'chunk_type': 'warranty',
                    'content': content,
                    'content_length': len(content),
                    'drop': False,
                    'metadata': metadata_raw
                }
                chunks.append(chunk)
        
        # 문서 메타데이터
        document = {
            'doc_id': doc_id,
            'doc_type': 'criteria_warranty',
            'title': '소비자분쟁해결기준 - 품질보증기간',
            'source_org': 'KCA',
            'category_path': ['기준', '품질보증기간'],
            'url': None,
            'collected_at': None,
            'metadata': {
                'table_type': 'table3',
                'item_count': len(chunks)
            },
            'chunks': []
        }
        
        # 청크 최적화 및 인덱스 할당
        document['chunks'] = self._optimize_chunks(chunks)
        document['chunks'] = self._assign_chunk_indices(document['chunks'])
        self._validate_chunk_indices(document['doc_id'], document['chunks'])
        
        # 메타데이터 보강
        document = self._enrich_document(document)
        
        self.stats['documents'] += 1
        self.stats['chunks'] += len(document['chunks'])
        
        print(f"  ✅ {len(document['chunks'])}개 보증기간 청크")
        
        return {'documents': [document]}
    
    def transform_criteria_table4(self, file_path: str) -> Dict:
        """
        기준 데이터 변환 - table4 (내구연한)
        - 문서 단위: 전체 테이블 하나
        - 청크 단위: 각 품목별 내구연한
        """
        print(f"\n📋 기준 데이터 변환 (table4 - 내구연한): {file_path}")
        
        doc_id = 'criteria:table4'
        chunks = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                    
                data = json.loads(line)
                
                # embed_text를 content로 사용
                content = data.get('embed_text', '')
                metadata_raw = data.get('metadata', {})
                
                # stable_id를 chunk_id로 사용
                chunk_id = data.get('stable_id', f"{doc_id}::lifespan{len(chunks):04d}")
                
                chunk = {
                    'chunk_id': chunk_id,
                    'chunk_type': 'lifespan',
                    'content': content,
                    'content_length': len(content),
                    'drop': False,
                    'metadata': metadata_raw
                }
                chunks.append(chunk)
        
        # 문서 메타데이터
        document = {
            'doc_id': doc_id,
            'doc_type': 'criteria_lifespan',
            'title': '소비자분쟁해결기준 - 내구연한',
            'source_org': 'KCA',
            'category_path': ['기준', '내구연한'],
            'url': None,
            'collected_at': None,
            'metadata': {
                'table_type': 'table4',
                'item_count': len(chunks)
            },
            'chunks': []
        }
        
        # 청크 최적화 및 인덱스 할당
        document['chunks'] = self._optimize_chunks(chunks)
        document['chunks'] = self._assign_chunk_indices(document['chunks'])
        self._validate_chunk_indices(document['doc_id'], document['chunks'])
        
        # 메타데이터 보강
        document = self._enrich_document(document)
        
        self.stats['documents'] += 1
        self.stats['chunks'] += len(document['chunks'])
        
        print(f"  ✅ {len(document['chunks'])}개 내구연한 청크")
        
        return {'documents': [document]}
    
    def transform_criteria_table2(self, file_path: str) -> Dict:
        """
        기준 데이터 변환 - table2 (해결기준)
        - 문서 단위: 전체 테이블 하나
        - 청크 단위: 각 행 (row_idx는 무시하고 0-based로 재할당)
        """
        print(f"\n📋 기준 데이터 변환 (table2): {file_path}")
        
        doc_id = 'criteria:table2'
        chunks = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                
                # drop 플래그 확인
                if data.get('drop', False):
                    self.stats['skipped'] += 1
                    continue
                
                chunk = {
                    'chunk_id': data['chunk_id'],
                    'chunk_type': 'resolution_row',
                    'content': data['text'],
                    'content_length': len(data['text']),
                    'drop': False,
                    'metadata': {
                        'category': data.get('category'),
                        'item_group': data.get('item_group'),
                        'item': data.get('item'),
                        'dispute_type': data.get('dispute_type'),
                        'resolution': data.get('resolution'),
                        'laws': data.get('laws', [])
                    },
                    'category_path': [
                        data.get('category'),
                        data.get('item_group'),
                        data.get('item')
                    ] if data.get('category') else None
                }
                chunks.append(chunk)
        
        # 청크 최적화
        chunks = self._optimize_chunks(chunks)
        
        # 0-based 인덱스 할당
        chunks = self._assign_chunk_indices(chunks)
        
        document = {
            'doc_id': doc_id,
            'doc_type': 'criteria_resolution',
            'title': '소비자분쟁해결기준 - 품목별 해결기준',
            'source_org': 'KCA',
            'category_path': None,
            'url': None,
            'metadata': {'source': 'table2'},
            'chunks': chunks
        }
        
        self._validate_chunk_indices(doc_id, chunks)
        
        # 메타데이터 보강
        document = self._enrich_document(document)
        
        self.stats['documents'] += 1
        self.stats['chunks'] += len(chunks)
        
        print(f"  ✅ {document['title']}: {len(chunks)}개 청크 (최적화 완료)")
        
        return {'documents': [document]}
    
    def transform_mediation_kca(self, file_path: str) -> Dict:
        """
        KCA 분쟁조정사례 변환
        - 문서 단위: 사건번호별 (case_no)
        - 청크 단위: chunk_type별
        """
        print(f"\n⚖️  분쟁조정사례 변환 (KCA): {file_path}")
        
        cases = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                case_no = data['case_no']
                
                if case_no not in cases:
                    cases[case_no] = {
                        'doc_id': f"kca:mediation:{case_no}",
                        'doc_type': 'mediation_case',
                        'title': f"{case_no} 분쟁조정사례",
                        'source_org': 'KCA',
                        'category_path': None,
                        'url': None,
                        'metadata': {
                            'case_no': case_no,
                            'decision_date': data.get('decision_date'),
                            'agency': 'kca'
                        },
                        'chunks': []
                    }
                
                # 빈 content는 drop=True로 설정 (주로 law 타입 청크)
                content = data['text']
                is_empty = len(content.strip()) == 0
                
                chunk = {
                    'chunk_id': f"kca:mediation:{case_no}:{data['chunk_type']}:{len(cases[case_no]['chunks']):04d}",
                    'chunk_type': data['chunk_type'],
                    'content': content,
                    'content_length': len(content),
                    'drop': is_empty,  # 빈 content는 drop
                    'metadata': {}
                }
                cases[case_no]['chunks'].append(chunk)
        
        # 각 케이스별로 청크 최적화 후 0-based 인덱스 할당
        result = {'documents': []}
        
        for case_no, case_data in cases.items():
            # 청크 최적화
            case_data['chunks'] = self._optimize_chunks(case_data['chunks'])
            
            # 0-based 인덱스 할당
            case_data['chunks'] = self._assign_chunk_indices(case_data['chunks'])
            self._validate_chunk_indices(case_data['doc_id'], case_data['chunks'])
            
            # 메타데이터 보강
            case_data = self._enrich_document(case_data)
            
            result['documents'].append(case_data)
            
            self.stats['documents'] += 1
            self.stats['chunks'] += len(case_data['chunks'])
        
        print(f"  ✅ {len(cases)}개 사례, 총 {sum(len(c['chunks']) for c in cases.values())}개 청크 (최적화 완료)")
        
        return result
    
    def transform_mediation_ecmc(self, file_path: str) -> Dict:
        """ECMC 분쟁조정사례 변환"""
        print(f"\n⚖️  분쟁조정사례 변환 (ECMC): {file_path}")
        
        cases = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                case_no = data['case_no']
                
                if case_no not in cases:
                    cases[case_no] = {
                        'doc_id': f"ecmc:mediation:{case_no}",
                        'doc_type': 'mediation_case',
                        'title': f"{case_no} 분쟁조정사례",
                        'source_org': 'ECMC',
                        'category_path': None,
                        'url': None,
                        'metadata': {
                            'case_no': case_no,
                            'decision_date': data.get('decision_date'),
                            'agency': 'ecmc'
                        },
                        'chunks': []
                    }
                
                # 빈 content는 drop=True로 설정
                content = data['text']
                is_empty = len(content.strip()) == 0
                
                chunk = {
                    'chunk_id': f"ecmc:mediation:{case_no}:{data['chunk_type']}:{len(cases[case_no]['chunks']):04d}",
                    'chunk_type': data['chunk_type'],
                    'content': content,
                    'content_length': len(content),
                    'drop': data.get('drop', False) or is_empty,  # 기존 drop 플래그 또는 빈 content
                    'metadata': {}
                }
                cases[case_no]['chunks'].append(chunk)
        
        # 각 케이스별로 청크 최적화 후 0-based 인덱스 할당 (drop=true 포함)
        result = {'documents': []}
        
        for case_no, case_data in cases.items():
            # 청크 최적화
            case_data['chunks'] = self._optimize_chunks(case_data['chunks'])
            
            # 0-based 인덱스 할당
            case_data['chunks'] = self._assign_chunk_indices(case_data['chunks'])
            self._validate_chunk_indices(case_data['doc_id'], case_data['chunks'])
            
            # 메타데이터 보강
            case_data = self._enrich_document(case_data)
            
            result['documents'].append(case_data)
            
            self.stats['documents'] += 1
            self.stats['chunks'] += len(case_data['chunks'])
        
        print(f"  ✅ {len(cases)}개 사례, 총 {sum(len(c['chunks']) for c in cases.values())}개 청크 (최적화 완료)")
        
        return result
    
    def transform_counsel_case(self, file_path: str) -> Dict:
        """
        피해구제사례 변환
        - 이미 doc_id, chunk_id, chunk_index가 존재
        - 검증만 수행
        """
        print(f"\n💬 피해구제사례 변환: {file_path}")
        
        documents = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                doc_id = data['doc_id']
                
                if doc_id not in documents:
                    documents[doc_id] = {
                        'doc_id': doc_id,
                        'doc_type': 'counsel_case',
                        'title': data['title'],
                        'source_org': 'consumer.go.kr',
                        'category_path': data.get('category_path', []),
                        'url': data.get('metadata', {}).get('url'),
                        'metadata': data.get('metadata', {}),
                        'chunks': []
                    }
                
                chunk = {
                    'chunk_id': data['chunk_id'],
                    'chunk_index': data['chunk_index'],  # 이미 0-based
                    'chunk_total': data['chunk_total'],
                    'chunk_type': 'qa_combined',
                    'content': data['text'],
                    'content_length': len(data['text']),
                    'drop': False,
                    'metadata': {}
                }
                documents[doc_id]['chunks'].append(chunk)
        
        # 청크 최적화 후 검증
        result = {'documents': []}
        
        for doc_id, doc_data in documents.items():
            # 청크 최적화
            doc_data['chunks'] = self._optimize_chunks(doc_data['chunks'])
            
            # 인덱스 재할당
            doc_data['chunks'] = self._assign_chunk_indices(doc_data['chunks'])
            
            # 검증
            self._validate_chunk_indices(doc_id, doc_data['chunks'])
            
            # 메타데이터 보강
            doc_data = self._enrich_document(doc_data)
            
            result['documents'].append(doc_data)
            
            self.stats['documents'] += 1
            self.stats['chunks'] += len(doc_data['chunks'])
        
        print(f"  ✅ {len(documents)}개 사례, 총 {sum(len(d['chunks']) for d in documents.values())}개 청크 (최적화 완료)")
        
        return result
    
    def run_transformation(self):
        """전체 데이터 변환 실행"""
        print("=" * 80)
        print("데이터 변환 시작")
        print("=" * 80)
        
        all_results = []
        
        # 1. 법령 데이터 (샘플로 1개만)
        print("\n" + "=" * 80)
        print("1. 법령 데이터 변환")
        print("=" * 80)
        
        law_file = DATA_DIR / 'law' / 'Civil_Law_chunks.jsonl'
        if law_file.exists():
            result = self.transform_law_data(str(law_file))
            self._save_json(result, 'law_civil_law.json')
            all_results.append(result)
        else:
            print(f"  ⚠️  파일을 찾을 수 없습니다: {law_file}")
            print(f"  현재 작업 디렉토리: {Path.cwd()}")
        
        # 2. 기준 데이터
        print("\n" + "=" * 80)
        print("2. 기준 데이터 변환")
        print("=" * 80)
        
        table2_file = DATA_DIR / 'criteria' / 'table2_resolution_row_chunks.jsonl'
        if table2_file.exists():
            result = self.transform_criteria_table2(str(table2_file))
            self._save_json(result, 'criteria_table2.json')
            all_results.append(result)
        else:
            print(f"  ⚠️  파일을 찾을 수 없습니다: {table2_file}")
            print(f"  현재 작업 디렉토리: {Path.cwd()}")
        
        # 3. 분쟁조정사례 (샘플)
        print("\n" + "=" * 80)
        print("3. 분쟁조정사례 변환")
        print("=" * 80)
        
        kca_file = DATA_DIR / 'dispute_resolution' / 'kca_final.jsonl'
        if kca_file.exists():
            result = self.transform_mediation_kca(str(kca_file))
            self._save_json(result, 'mediation_kca.json')
            all_results.append(result)
        else:
            print(f"  ⚠️  파일을 찾을 수 없습니다: {kca_file}")
            print(f"  현재 작업 디렉토리: {Path.cwd()}")
        
        ecmc_file = DATA_DIR / 'dispute_resolution' / 'ecmc_final_rag_chunks_normalized.jsonl'
        if ecmc_file.exists():
            result = self.transform_mediation_ecmc(str(ecmc_file))
            self._save_json(result, 'mediation_ecmc.json')
            all_results.append(result)
        else:
            print(f"  ⚠️  파일을 찾을 수 없습니다: {ecmc_file}")
            print(f"  현재 작업 디렉토리: {Path.cwd()}")
        
        # 4. 피해구제사례 (샘플로 1개만)
        print("\n" + "=" * 80)
        print("4. 피해구제사례 변환")
        print("=" * 80)
        
        counsel_file = DATA_DIR / 'compensation_case' / 'cs_114_chunks_v2.jsonl'
        if counsel_file.exists():
            result = self.transform_counsel_case(str(counsel_file))
            self._save_json(result, 'counsel_cs_114.json')
            all_results.append(result)
        else:
            print(f"  ⚠️  파일을 찾을 수 없습니다: {counsel_file}")
            print(f"  현재 작업 디렉토리: {Path.cwd()}")
        
        # 전체 통계
        print("\n" + "=" * 80)
        print("변환 완료 통계")
        print("=" * 80)
        print(f"  - 총 문서: {self.stats['documents']:,}개")
        print(f"  - 총 청크: {self.stats['chunks']:,}개")
        print(f"  - 스킵: {self.stats['skipped']:,}개")
        if self.enrich_metadata:
            print(f"  - 메타데이터 보강: {self.stats['enriched_chunks']:,}개 청크")
        print(f"  - 오류: {len(self.stats['errors'])}개")
        
        if self.stats['errors']:
            print("\n오류 목록:")
            for error in self.stats['errors']:
                print(f"  - {error}")
        
        # 통합 통계 저장
        summary = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'files': {
                'law': 1,
                'criteria': 1,
                'mediation': 2,
                'counsel': 1
            }
        }
        self._save_json(summary, 'transformation_summary.json')
        
        print(f"\n✅ 변환 완료! 결과는 {self.output_dir}/ 에 저장되었습니다.")
        
        return all_results
    
    def close(self):
        """리소스 정리"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

def main():
    """메인 함수"""
    transformer = DataTransformer(
        use_db=False  # 일단 JSON만 생성
    )
    
    try:
        transformer.run_transformation()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        transformer.close()

if __name__ == '__main__':
    main()
