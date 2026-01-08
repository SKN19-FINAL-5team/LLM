"""
Case Retriever Module
사례 전용 검색기 - 벡터 유사도 + chunk_type 가중치 + 최신성 + 기관 적합성 결합
"""

import psycopg2
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from ..query_analyzer import QueryAnalysis


@dataclass
class CaseSearchResult:
    """사례 검색 결과"""
    chunk_id: str
    doc_id: str
    content: str
    chunk_type: str
    case_no: Optional[str]
    decision_date: Optional[str]
    agency: Optional[str]
    category_path: List[str]
    vector_similarity: float     # 벡터 유사도
    chunk_type_weight: float     # chunk type 가중치
    recency_score: float         # 최신성 점수
    agency_score: float          # 기관 적합성 점수
    final_score: float           # 최종 점수
    metadata: Dict


class CaseRetriever:
    """사례 전용 검색기"""
    
    # 가중치 설정
    VECTOR_WEIGHT = 0.4         # 벡터 유사도
    CHUNK_TYPE_WEIGHT = 0.3     # chunk type 중요도
    RECENCY_WEIGHT = 0.2        # 최신성
    AGENCY_WEIGHT = 0.1         # 기관 적합성
    
    # Chunk Type별 중요도
    # Phase 1 개선: 가중치 감소 (Case 우세 방지)
    CHUNK_TYPE_IMPORTANCE = {
        'judgment': 1.2,           # 판단 (1.5 → 1.2)
        'decision': 1.2,           # 결정 (1.5 → 1.2)
        'answer': 1.1,             # 답변 (1.4 → 1.1)
        'qa_combined': 1.1,        # Q&A 결합 (1.3 → 1.1)
        'parties_claim': 1.0,      # 당사자 주장 (1.1 → 1.0)
        'case_overview': 1.0,      # 사건 개요
        'question': 0.9,           # 질문 (0.8 → 0.9)
        'default': 1.0             # 기본값
    }
    
    def __init__(self, db_config: Dict):
        """
        Args:
            db_config: 데이터베이스 연결 설정
        """
        self.db_config = db_config
        self.conn = None
        self.cur = None
    
    def connect_db(self):
        """DB 연결"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
            self.cur = self.conn.cursor()
    
    def close_db(self):
        """DB 연결 종료"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
    
    def search(
        self,
        query: str,
        query_analysis: QueryAnalysis,
        query_embedding: List[float],
        agencies: Optional[List[str]] = None,
        top_k: int = 10,
        min_similarity: float = 0.25,
        debug: bool = False
    ) -> List[CaseSearchResult]:
        """
        사례 검색
        
        Args:
            query: 원본 쿼리
            query_analysis: 쿼리 분석 결과
            query_embedding: 쿼리 임베딩 벡터
            agencies: 선호 기관 리스트 (선택)
            top_k: 반환할 최대 결과 수
            min_similarity: 최소 유사도 임계값
            debug: 디버깅 로그 출력 여부
        
        Returns:
            사례 검색 결과 리스트
        """
        self.connect_db()
        
        # DEBUG: 입력 정보 확인
        if debug:
            print(f"\n[Case Retriever DEBUG]")
            print(f"  Query: {query}")
            print(f"  - Agencies filter: {agencies}")
            print(f"  - Min similarity: {min_similarity}")
            print(f"  - Query type: {query_analysis.query_type}")
            print(f"  - Keywords: {query_analysis.keywords[:5] if len(query_analysis.keywords) > 5 else query_analysis.keywords}")
        
        # 벡터 유사도 검색 (넉넉하게 가져옴)
        vector_results = self._vector_search(
            query_embedding,
            agencies=agencies,
            top_k=top_k * 3,
            min_similarity=min_similarity,
            debug=debug
        )
        
        if debug:
            print(f"  - Vector search results: {len(vector_results)}")
        
        # 점수 계산 및 재랭킹
        scored_results = []
        for result in vector_results:
            # Chunk type 가중치
            chunk_type_weight = self.CHUNK_TYPE_IMPORTANCE.get(
                result.chunk_type,
                self.CHUNK_TYPE_IMPORTANCE['default']
            )
            result.chunk_type_weight = chunk_type_weight
            
            # 최신성 점수
            result.recency_score = self._calculate_recency_score(
                result.decision_date
            )
            
            # 기관 적합성 점수
            result.agency_score = self._calculate_agency_score(
                result.agency,
                agencies
            )
            
            # 최종 점수 계산
            result.final_score = (
                result.vector_similarity * self.VECTOR_WEIGHT +
                chunk_type_weight * self.CHUNK_TYPE_WEIGHT +
                result.recency_score * self.RECENCY_WEIGHT +
                result.agency_score * self.AGENCY_WEIGHT
            )
            
            scored_results.append(result)
            
            if debug and len(scored_results) <= 3:
                print(f"    > Result {len(scored_results)}: sim={result.vector_similarity:.3f}, final={result.final_score:.3f}, chunk_type={result.chunk_type}")
        
        # 상위 K개 반환
        scored_results.sort(key=lambda x: x.final_score, reverse=True)
        
        if debug:
            print(f"  - Final results after scoring: {len(scored_results[:top_k])}")
            if scored_results:
                print(f"  - Top score: {scored_results[0].final_score:.3f}")
            else:
                print(f"  - ❌ NO RESULTS RETURNED")
        
        return scored_results[:top_k]
    
    def _vector_search(
        self,
        query_embedding: List[float],
        agencies: Optional[List[str]] = None,
        top_k: int = 30,
        min_similarity: float = 0.25,
        debug: bool = False
    ) -> List[CaseSearchResult]:
        """
        벡터 유사도 검색
        
        Args:
            query_embedding: 쿼리 임베딩
            agencies: 기관 필터 (선택)
            top_k: 반환할 최대 결과 수
            min_similarity: 최소 유사도
            debug: 디버깅 로그 출력 여부
        
        Returns:
            검색 결과 리스트
        """
        # SQL 쿼리 구성 - 명시적 doc_type 지정
        sql = """
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                c.chunk_type,
                d.metadata->>'case_no' AS case_no,
                d.metadata->>'case_sn' AS case_sn,
                d.metadata->>'decision_date' AS decision_date,
                d.source_org AS agency,
                d.category_path,
                d.metadata,
                1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type IN ('counsel_case', 'mediation_case')
                AND c.drop = FALSE
                AND c.embedding IS NOT NULL
                AND (1 - (c.embedding <=> %s::vector)) >= %s
        """
        
        params = [query_embedding, query_embedding, min_similarity]
        
        # 기관 필터 (선택적)
        if agencies and len(agencies) > 0:
            placeholders = ','.join(['%s'] * len(agencies))
            sql += f" AND d.source_org IN ({placeholders})"
            params.extend(agencies)
            if debug:
                print(f"    > Applying agency filter: {agencies}")
        
        sql += """
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """
        params.extend([query_embedding, top_k])
        
        if debug:
            print(f"    > Executing vector search (min_similarity={min_similarity}, top_k={top_k})")
        
        self.cur.execute(sql, params)
        rows = self.cur.fetchall()
        
        if debug:
            print(f"    > Found {len(rows)} raw results")
        
        results = []
        for row in rows:
            (chunk_id, doc_id, content, chunk_type, case_no, case_sn,
             decision_date, agency, category_path, metadata, similarity) = row
            
            # case_no 우선, 없으면 case_sn 사용
            case_number = case_no or case_sn
            
            results.append(CaseSearchResult(
                chunk_id=chunk_id,
                doc_id=doc_id,
                content=content,
                chunk_type=chunk_type or 'default',
                case_no=case_number,
                decision_date=decision_date,
                agency=agency,
                category_path=category_path or [],
                vector_similarity=float(similarity),
                chunk_type_weight=0.0,  # 나중에 계산
                recency_score=0.0,      # 나중에 계산
                agency_score=0.0,       # 나중에 계산
                final_score=0.0,        # 나중에 계산
                metadata=metadata or {}
            ))
        
        return results
    
    def _calculate_recency_score(self, decision_date: Optional[str]) -> float:
        """
        최신성 점수 계산
        
        최근 사례일수록 높은 점수
        
        Args:
            decision_date: 결정 날짜 (YYYY 또는 YYYY-MM-DD)
        
        Returns:
            최신성 점수 (0~1)
        """
        if not decision_date:
            return 0.5  # 날짜 정보 없으면 중간 점수
        
        try:
            # 연도 추출
            year_str = str(decision_date)[:4]
            if not year_str.isdigit():
                return 0.5
            
            year = int(year_str)
            current_year = datetime.now().year
            
            # 최근 10년 기준으로 점수 계산
            years_ago = current_year - year
            
            if years_ago < 0:
                return 0.5  # 미래 날짜는 중간 점수
            elif years_ago == 0:
                return 1.0  # 올해 사례
            elif years_ago <= 2:
                return 0.9  # 2년 이내
            elif years_ago <= 5:
                return 0.7  # 5년 이내
            elif years_ago <= 10:
                return 0.5  # 10년 이내
            else:
                return 0.3  # 10년 초과
        
        except Exception:
            return 0.5
    
    def _calculate_agency_score(
        self,
        result_agency: Optional[str],
        preferred_agencies: Optional[List[str]]
    ) -> float:
        """
        기관 적합성 점수 계산
        
        Args:
            result_agency: 검색 결과의 기관
            preferred_agencies: 선호 기관 리스트
        
        Returns:
            기관 적합성 점수 (0~1)
        """
        if not preferred_agencies or not result_agency:
            return 0.5  # 기본 점수
        
        # 대소문자 무시 비교
        result_agency_lower = result_agency.lower()
        preferred_lower = [a.lower() for a in preferred_agencies]
        
        if result_agency_lower in preferred_lower:
            return 1.0  # 선호 기관 일치
        else:
            return 0.3  # 다른 기관
