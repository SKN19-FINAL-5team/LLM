"""
로컬 환경용 RAG 시스템 테스트 스크립트
Hybrid Search, BM25, Cosine Similarity 3가지 검색 방법을 비교하고 LLM 분석을 포함합니다.

사용법:
    python backend/scripts/test_rag_local_simple.py
    python backend/scripts/test_rag_local_simple.py --query "냉장고 환불 사례"
"""

import os
import sys
import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from dotenv import load_dotenv

# 프로젝트 경로 추가
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

# 환경 변수 로드
load_dotenv()

from app.rag.multi_method_retriever import MultiMethodRetriever
from app.rag.retriever import VectorRetriever
from app.rag.generator import RAGGenerator


class SimpleRAGTester:
    """로컬 환경용 간단한 RAG 테스터"""
    
    def __init__(self, db_config: dict):
        """
        Args:
            db_config: 데이터베이스 연결 설정
        """
        self.db_config = db_config
        self.retriever = None
        self.vector_retriever = None  # 순차 검색용
        self.generator = None
        # logs 폴더 경로 설정
        self.logs_dir = backend_dir / 'logs'
        self._ensure_logs_dir()
        
    def _ensure_logs_dir(self):
        """logs 폴더가 없으면 생성"""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        # .gitkeep 파일 생성 (빈 폴더도 git에 포함되도록)
        gitkeep_file = self.logs_dir / '.gitkeep'
        if not gitkeep_file.exists():
            gitkeep_file.touch()
    
    def initialize(self):
        """검색기와 생성기 초기화"""
        print("🔧 RAG 시스템 초기화 중...")
        
        try:
            # MultiMethodRetriever 초기화 (SPLADE 제외)
            self.retriever = MultiMethodRetriever(self.db_config)
            print("✅ MultiMethodRetriever 초기화 완료")
            
            # VectorRetriever 초기화 (순차 검색용)
            self.vector_retriever = VectorRetriever(self.db_config)
            print("✅ VectorRetriever 초기화 완료")
            
            # RAGGenerator 초기화
            self.generator = RAGGenerator()
            print("✅ RAGGenerator 초기화 완료")
            
        except Exception as e:
            print(f"❌ 초기화 실패: {e}")
            raise
    
    def _search_by_doc_type(
        self,
        query: str,
        doc_type: str,
        top_k: int = 10
    ) -> List[Dict]:
        """
        doc_type으로 필터링된 검색
        
        Args:
            query: 검색 쿼리
            doc_type: 문서 타입 (예: 'mediation_case', 'counsel_case', 'law')
            top_k: 반환할 최대 결과 수
        
        Returns:
            검색된 청크 리스트
        """
        self.vector_retriever.connect_db()
        
        # 쿼리 임베딩
        query_embedding = self.vector_retriever.embed_query(query)
        
        # SQL 쿼리 구성 (doc_type 필터 추가)
        sql = """
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.chunk_type,
                c.content,
                c.content_length,
                d.title,
                d.metadata->>'decision_date' AS decision_date,
                d.source_org AS agency,
                d.doc_type AS source,
                1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.drop = FALSE
                AND d.doc_type = %s
        """
        
        params = [query_embedding, doc_type]
        
        sql += """
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """
        params.append(query_embedding)
        params.append(top_k)
        
        # 쿼리 실행
        with self.vector_retriever.conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        
        # 결과 포맷팅
        results = []
        for row in rows:
            results.append({
                'chunk_id': row[0],
                'doc_id': row[1],
                'chunk_type': row[2],
                'text': row[3],
                'text_len': row[4],
                'case_no': row[5],
                'decision_date': row[6],
                'agency': row[7],
                'source': row[8],
                'similarity': float(row[9])
            })
        
        return results
    
    def _get_document_full_text(self, doc_id: str) -> str:
        """
        같은 doc_id의 모든 chunks를 가져와서 텍스트 합치기
        
        Args:
            doc_id: 문서 ID
        
        Returns:
            문서 전체 텍스트 (모든 chunks 합친 것)
        """
        chunks = self.vector_retriever.get_case_chunks(doc_id)
        # chunk_index 순서로 정렬 (seq 필드 사용)
        chunks.sort(key=lambda x: x.get('seq', 0))
        # 모든 텍스트 합치기
        full_text = '\n\n'.join(chunk.get('text', '') for chunk in chunks)
        return full_text
    
    def _enrich_with_full_text(self, results: List[Dict]) -> List[Dict]:
        """
        검색 결과에 문서 전체 텍스트 추가
        
        Args:
            results: 검색 결과 리스트
        
        Returns:
            raw_text 필드가 추가된 결과 리스트
        """
        enriched_results = []
        seen_doc_ids = set()  # 중복 제거용
        
        for result in results:
            doc_id = result.get('doc_id') or result.get('case_uid')
            if not doc_id:
                continue
            
            # 이미 처리한 doc_id는 건너뛰기
            if doc_id in seen_doc_ids:
                continue
            seen_doc_ids.add(doc_id)
            
            try:
                # 문서 전체 텍스트 가져오기
                raw_text = self._get_document_full_text(doc_id)
                
                # chunks 개수 가져오기
                chunks = self.vector_retriever.get_case_chunks(doc_id)
                chunks_count = len(chunks)
                
                # 결과에 추가 정보 포함
                enriched_result = result.copy()
                enriched_result['raw_text'] = raw_text
                enriched_result['chunks_count'] = chunks_count
                enriched_result['doc_id'] = doc_id
                enriched_result['chunk_id'] = result.get('chunk_id') or result.get('chunk_uid')
                
                enriched_results.append(enriched_result)
            except Exception as e:
                print(f"⚠️  문서 전체 텍스트 가져오기 실패 (doc_id: {doc_id}): {e}")
                # 실패해도 원본 결과는 포함
                enriched_result = result.copy()
                enriched_result['raw_text'] = result.get('text', '')
                enriched_result['chunks_count'] = 1
                enriched_results.append(enriched_result)
        
        return enriched_results
    
    def _search_sequential(
        self,
        query: str,
        top_k: int = 10,
        min_threshold: int = 2
    ) -> List[Dict]:
        """
        순차 검색 로직: 분쟁조정사례 → 상담사례 → 법령+기준
        
        Args:
            query: 검색 쿼리
            top_k: 각 단계별 반환할 최대 결과 수
            min_threshold: 최소 결과 수 임계값
        
        Returns:
            검색 결과 리스트 (raw_text 포함)
        """
        all_results = []
        
        # 1순위: 분쟁조정사례
        print(f"[1순위] 분쟁조정사례 검색 중...")
        mediation_results = self._search_by_doc_type(
            query=query,
            doc_type='mediation_case',
            top_k=top_k
        )
        print(f"  - 분쟁조정사례: {len(mediation_results)}건")
        
        if len(mediation_results) >= min_threshold:
            print(f"  ✅ 분쟁조정사례 충분 ({len(mediation_results)}건 >= {min_threshold}건), 검색 종료")
            return self._enrich_with_full_text(mediation_results)
        
        all_results.extend(mediation_results)
        
        # 2순위: 상담사례
        print(f"[2순위] 상담사례 검색 중...")
        counsel_results = self._search_by_doc_type(
            query=query,
            doc_type='counsel_case',
            top_k=top_k
        )
        print(f"  - 상담사례: {len(counsel_results)}건")
        
        all_results.extend(counsel_results)
        if len(all_results) >= min_threshold:
            print(f"  ✅ 결과 충분 ({len(all_results)}건 >= {min_threshold}건), 검색 종료")
            return self._enrich_with_full_text(all_results)
        
        # 3순위: 법령 + 분쟁조정기준
        print(f"[3순위] 법령 및 분쟁조정기준 검색 중...")
        law_results = self._search_by_doc_type(
            query=query,
            doc_type='law',
            top_k=top_k
        )
        print(f"  - 법령: {len(law_results)}건")
        
        # 기준 검색 (criteria_* 타입들)
        criteria_types = ['criteria_item', 'criteria_resolution', 'criteria_warranty', 'criteria_lifespan']
        criteria_results = []
        for criteria_type in criteria_types:
            try:
                results = self._search_by_doc_type(
                    query=query,
                    doc_type=criteria_type,
                    top_k=top_k // len(criteria_types)  # 균등 분배
                )
                criteria_results.extend(results)
            except Exception as e:
                print(f"  ⚠️  {criteria_type} 검색 실패: {e}")
        
        print(f"  - 분쟁조정기준: {len(criteria_results)}건")
        
        all_results.extend(law_results)
        all_results.extend(criteria_results)
        
        print(f"  ✅ 전체 검색 완료: 총 {len(all_results)}건")
        return self._enrich_with_full_text(all_results)
    
    def test_query(
        self,
        query: str,
        top_k: int = 10,
        show_details: bool = False
    ):
        """
        단일 쿼리에 대해 순차 검색 및 문서 전체 텍스트 반환 테스트
        
        Args:
            query: 검색 쿼리
            top_k: 각 단계별 반환할 최대 결과 수
            show_details: 상세 결과 출력 여부
        """
        print("\n" + "="*80)
        print(f"📝 검색 쿼리: {query}")
        print("="*80)
        
        print(f"\n🔍 순차 검색 실행 중...")
        print(f"📊 각 단계별 Top-{top_k} 결과 검색\n")
        
        try:
            # 순차 검색 실행
            sequential_results = self._search_sequential(
                query=query,
                top_k=top_k,
                min_threshold=2
            )
            
            print(f"\n✅ 순차 검색 완료: 총 {len(sequential_results)}건")
            
            # 상세 결과 출력 (선택사항)
            if show_details:
                self._print_sequential_results(sequential_results)
            
            # 결과를 MultiMethodRetriever 형식으로 변환 (LLM 분석용)
            method_results = self._convert_to_method_results(sequential_results, query)
            
            # LLM 비교 분석
            print("\n" + "="*80)
            print("🤖 LLM 비교 분석 중...")
            print("="*80 + "\n")
            
            analysis_result = self.generator.generate_comparative_answer(
                query=query,
                method_results=method_results,
                temperature=0.3,
                max_tokens=1500
            )
            
            # LLM 분석 결과 출력
            print(analysis_result['answer'])
            
            # 메타데이터 출력
            print("\n" + "-"*80)
            print("📊 검색 통계:")
            print(f"  - 검색된 문서 수: {len(sequential_results)}개")
            if sequential_results:
                sources = {}
                for result in sequential_results:
                    source = result.get('source', 'unknown')
                    sources[source] = sources.get(source, 0) + 1
                print(f"  - 문서 유형별 분포:")
                for source, count in sources.items():
                    print(f"    - {source}: {count}개")
            print(f"  - 사용된 토큰 수: {analysis_result['usage']['total_tokens']:,}개")
            print(f"    (프롬프트: {analysis_result['usage']['prompt_tokens']:,}, 생성: {analysis_result['usage']['completion_tokens']:,})")
            print("-"*80)
            
            # JSON 파일로 저장
            saved_path = self._save_sequential_results_to_json(query, sequential_results)
            if saved_path:
                print(f"\n💾 검색 결과가 저장되었습니다: {saved_path}")
            
            return {
                'query': query,
                'sequential_results': sequential_results,
                'method_results': method_results,
                'analysis': analysis_result
            }
            
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _print_search_summary(self, method_results: dict):
        """검색 결과 요약 출력"""
        print("📈 검색 결과 요약:")
        print("-"*80)
        
        for method_name, method_data in method_results.get('methods', {}).items():
            if method_data.get('success', False):
                count = method_data.get('count', 0)
                elapsed = method_data.get('elapsed_time', 0)
                print(f"  ✅ {method_name.upper():8s}: {count:3d}개 결과 ({elapsed*1000:6.1f}ms)")
            else:
                error = method_data.get('error', 'Unknown error')
                print(f"  ❌ {method_name.upper():8s}: 실패 - {error}")
        
        print("-"*80)
    
    def _print_detailed_results(self, method_results: dict):
        """각 검색 방법별 상세 결과 출력"""
        print("\n📋 상세 검색 결과:")
        print("="*80)
        
        for method_name, method_data in method_results.get('methods', {}).items():
            if not method_data.get('success', False):
                continue
            
            results = method_data.get('results', [])
            if not results:
                print(f"\n[{method_name.upper()}] 결과 없음")
                continue
            
            print(f"\n[{method_name.upper()}] 상위 {len(results)}개 결과:")
            print("-"*80)
            
            for idx, result in enumerate(results[:5], 1):  # 상위 5개만 출력
                print(f"\n{idx}. 점수: {result.get('score', 0):.4f}")
                print(f"   출처: {result.get('source', 'N/A')}")
                if result.get('case_no'):
                    print(f"   사건번호: {result.get('case_no')}")
                if result.get('agency'):
                    print(f"   기관: {result.get('agency')}")
                if result.get('decision_date'):
                    print(f"   결정일자: {result.get('decision_date')}")
                
                text = result.get('text', '') or result.get('content', '')
                if text:
                    preview = text[:200] + "..." if len(text) > 200 else text
                    print(f"   내용: {preview}")
    
    def _print_sequential_results(self, results: List[Dict]):
        """순차 검색 결과 상세 출력"""
        print("\n📋 순차 검색 상세 결과:")
        print("="*80)
        
        for idx, result in enumerate(results[:10], 1):  # 상위 10개만 출력
            print(f"\n{idx}. 유사도: {result.get('similarity', 0):.4f}")
            print(f"   출처: {result.get('source', 'N/A')}")
            print(f"   문서 ID: {result.get('doc_id', 'N/A')}")
            if result.get('case_no'):
                print(f"   사건번호: {result.get('case_no')}")
            if result.get('agency'):
                print(f"   기관: {result.get('agency')}")
            if result.get('decision_date'):
                print(f"   결정일자: {result.get('decision_date')}")
            if result.get('chunks_count'):
                print(f"   청크 수: {result.get('chunks_count')}개")
            
            raw_text = result.get('raw_text', '')
            if raw_text:
                preview = raw_text[:300] + "..." if len(raw_text) > 300 else raw_text
                print(f"   전체 텍스트 미리보기: {preview}")
    
    def _convert_to_method_results(self, sequential_results: List[Dict], query: str) -> Dict:
        """
        순차 검색 결과를 MultiMethodRetriever 형식으로 변환
        
        Args:
            sequential_results: 순차 검색 결과
            query: 검색 쿼리
        
        Returns:
            MultiMethodRetriever 형식의 결과 딕셔너리
        """
        # cosine 방법으로 변환 (순차 검색은 cosine similarity 기반)
        normalized_results = []
        for result in sequential_results:
            normalized = {
                'chunk_id': result.get('chunk_id'),
                'doc_id': result.get('doc_id'),
                'text': result.get('raw_text', result.get('text', '')),
                'chunk_type': result.get('chunk_type'),
                'source': result.get('source'),
                'agency': result.get('agency'),
                'case_no': result.get('case_no'),
                'decision_date': result.get('decision_date'),
                'method': 'cosine',
                'score': result.get('similarity', 0.0)
            }
            normalized_results.append(normalized)
        
        return {
            'query': query,
            'methods': {
                'cosine': {
                    'method': 'cosine',
                    'results': normalized_results,
                    'count': len(normalized_results),
                    'elapsed_time': 0.0,
                    'success': True
                }
            },
            'total_methods': 1,
            'successful_methods': 1
        }
    
    def _sanitize_filename(self, text: str, max_length: int = 20) -> str:
        """
        파일명으로 사용할 수 있도록 텍스트 정리
        
        Args:
            text: 정리할 텍스트
            max_length: 최대 길이
        
        Returns:
            정리된 파일명 문자열
        """
        # 한글, 영문, 숫자는 유지, 나머지는 언더스코어로 변환
        sanitized = re.sub(r'[^\w가-힣]', '_', text)
        # 연속된 언더스코어를 하나로
        sanitized = re.sub(r'_+', '_', sanitized)
        # 앞뒤 언더스코어 제거
        sanitized = sanitized.strip('_')
        # 길이 제한
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        return sanitized
    
    def _save_sequential_results_to_json(self, query: str, sequential_results: List[Dict]) -> Optional[Path]:
        """
        순차 검색 결과를 JSON 파일로 저장
        
        Args:
            query: 검색 쿼리
            sequential_results: 순차 검색 결과 리스트
        
        Returns:
            저장된 파일 경로 (실패 시 None)
        """
        try:
            # 타임스탬프 생성
            now = datetime.now()
            timestamp = now.strftime('%Y%m%d_%H%M%S')
            
            # 쿼리에서 파일명 생성 (최대 20자)
            query_part = self._sanitize_filename(query, max_length=20)
            if not query_part:
                query_part = 'query'
            
            # 파일명 생성
            filename = f"rag_test_{timestamp}_{query_part}.json"
            filepath = self.logs_dir / filename
            
            # 저장할 데이터 구조화
            save_data = {
                'query': query,
                'timestamp': now.isoformat(),
                'search_type': 'sequential',
                'results': []
            }
            
            # 각 결과 저장
            for result in sequential_results:
                result_data = {
                    'chunk_id': result.get('chunk_id'),
                    'doc_id': result.get('doc_id'),
                    'raw_text': result.get('raw_text', ''),
                    'score': result.get('similarity', 0.0),
                    'source': result.get('source'),
                    'agency': result.get('agency'),
                    'case_no': result.get('case_no'),
                    'decision_date': result.get('decision_date'),
                    'chunk_type': result.get('chunk_type'),
                    'chunks_count': result.get('chunks_count', 0)
                }
                save_data['results'].append(result_data)
            
            # 통계 정보 추가
            save_data['statistics'] = {
                'total_results': len(sequential_results),
                'sources': {}
            }
            
            for result in sequential_results:
                source = result.get('source', 'unknown')
                save_data['statistics']['sources'][source] = save_data['statistics']['sources'].get(source, 0) + 1
            
            # JSON 파일로 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            return filepath
            
        except Exception as e:
            print(f"⚠️  JSON 저장 실패: {e}")
            return None
    
    def _save_results_to_json(self, query: str, method_results: Dict) -> Optional[Path]:
        """
        검색 결과를 JSON 파일로 저장
        
        Args:
            query: 검색 쿼리
            method_results: 검색 결과 딕셔너리
        
        Returns:
            저장된 파일 경로 (실패 시 None)
        """
        try:
            # 타임스탬프 생성
            now = datetime.now()
            timestamp = now.strftime('%Y%m%d_%H%M%S')
            
            # 쿼리에서 파일명 생성 (최대 20자)
            query_part = self._sanitize_filename(query, max_length=20)
            if not query_part:
                query_part = 'query'
            
            # 파일명 생성
            filename = f"rag_test_{timestamp}_{query_part}.json"
            filepath = self.logs_dir / filename
            
            # 저장할 데이터 구조화
            save_data = {
                'query': query,
                'timestamp': now.isoformat(),
                'search_methods': {}
            }
            
            # 각 검색 방법별 결과 저장
            for method_name, method_data in method_results.get('methods', {}).items():
                save_data['search_methods'][method_name] = {
                    'success': method_data.get('success', False),
                    'count': method_data.get('count', 0),
                    'elapsed_time': method_data.get('elapsed_time', 0),
                    'results': []
                }
                
                if method_data.get('success', False):
                    # 각 결과 저장 (필요한 필드만)
                    for result in method_data.get('results', []):
                        result_data = {
                            'chunk_id': result.get('chunk_id'),
                            'doc_id': result.get('doc_id'),
                            'text': result.get('text') or result.get('content', ''),
                            'score': result.get('score', 0.0),
                            'source': result.get('source'),
                            'agency': result.get('agency'),
                            'case_no': result.get('case_no'),
                            'decision_date': result.get('decision_date'),
                            'chunk_type': result.get('chunk_type')
                        }
                        save_data['search_methods'][method_name]['results'].append(result_data)
                else:
                    save_data['search_methods'][method_name]['error'] = method_data.get('error', 'Unknown error')
            
            # 통계 정보 추가
            save_data['statistics'] = {
                'total_results': sum(
                    m.get('count', 0) 
                    for m in method_results.get('methods', {}).values()
                ),
                'successful_methods': sum(
                    1 for m in method_results.get('methods', {}).values()
                    if m.get('success', False)
                ),
                'total_methods': len(method_results.get('methods', {}))
            }
            
            # JSON 파일로 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            return filepath
            
        except Exception as e:
            print(f"⚠️  JSON 저장 실패: {e}")
            return None
    
    def interactive_mode(self):
        """인터랙티브 모드"""
        print("\n" + "="*80)
        print("🎯 RAG 시스템 테스트 (인터랙티브 모드)")
        print("="*80)
        print("\n종료하려면 'quit', 'exit', 또는 'q'를 입력하세요.")
        print("상세 결과를 보려면 쿼리 앞에 '--detail' 또는 '-d'를 붙이세요.")
        print("예: --detail 냉장고 환불 사례\n")
        
        while True:
            try:
                user_input = input("\n검색 쿼리 입력: ").strip()
                
                if user_input.lower() in ('quit', 'exit', 'q'):
                    print("\n👋 테스트를 종료합니다.")
                    break
                
                if not user_input:
                    continue
                
                # 상세 모드 확인
                show_details = False
                if user_input.startswith('--detail') or user_input.startswith('-d'):
                    show_details = True
                    query = user_input.replace('--detail', '').replace('-d', '').strip()
                else:
                    query = user_input
                
                if not query:
                    print("⚠️  쿼리를 입력해주세요.")
                    continue
                
                # 테스트 실행
                self.test_query(query, top_k=10, show_details=show_details)
                
            except KeyboardInterrupt:
                print("\n\n👋 테스트가 중단되었습니다.")
                break
            except Exception as e:
                print(f"\n❌ 오류 발생: {e}")
    
    def close(self):
        """리소스 정리"""
        if self.retriever:
            self.retriever.close()
        if self.vector_retriever:
            self.vector_retriever.close()
        print("\n✅ 리소스 정리 완료")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='로컬 환경용 RAG 시스템 테스트 스크립트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 인터랙티브 모드
  python backend/scripts/test_rag_local_simple.py
  
  # 단일 쿼리 테스트
  python backend/scripts/test_rag_local_simple.py --query "냉장고 환불 사례"
  
  # 상세 결과 포함
  python backend/scripts/test_rag_local_simple.py --query "냉장고 환불 사례" --detail
        """
    )
    
    parser.add_argument(
        '--query', '-q',
        type=str,
        help='검색할 쿼리 (지정하지 않으면 인터랙티브 모드)'
    )
    
    parser.add_argument(
        '--detail', '-d',
        action='store_true',
        help='상세 검색 결과 출력'
    )
    
    parser.add_argument(
        '--top-k',
        type=int,
        default=10,
        help='각 방법별 반환할 최대 결과 수 (기본값: 10)'
    )
    
    args = parser.parse_args()
    
    # 데이터베이스 설정
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # 테스터 초기화
    tester = SimpleRAGTester(db_config)
    
    try:
        # 초기화
        tester.initialize()
        
        if args.query:
            # 단일 쿼리 테스트
            tester.test_query(
                query=args.query,
                top_k=args.top_k,
                show_details=args.detail
            )
        else:
            # 인터랙티브 모드
            tester.interactive_mode()
    
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        tester.close()


if __name__ == "__main__":
    main()
