"""
Criteria Retriever Module
기준 전용 검색기 - 품목명 매칭 + 분류 계층 + 분쟁유형 + 벡터 유사도 결합
"""

import psycopg2
from typing import List, Dict, Optional
from dataclasses import dataclass
from ..query_analyzer import QueryAnalysis


@dataclass
class CriteriaSearchResult:
    """기준 검색 결과"""
    chunk_id: str
    doc_id: str
    content: str
    item_name: Optional[str]
    category: Optional[str]
    industry: Optional[str]
    item_group: Optional[str]
    dispute_type: Optional[str]
    item_match_score: float       # 품목명 매칭 점수
    hierarchy_match_score: float  # 분류 계층 매칭 점수
    dispute_match_score: float    # 분쟁유형 매칭 점수
    vector_similarity: float      # 벡터 유사도
    final_score: float            # 최종 점수
    metadata: Dict


class CriteriaRetriever:
    """기준 전용 검색기 (Phase 2 개선)"""
    
    # 가중치 설정 (Phase 2: 품목명 우선)
    ITEM_MATCH_WEIGHT = 0.6      # 품목명 매칭 (0.4 → 0.6, 최우선)
    KEYWORD_WEIGHT = 0.2         # 키워드 매칭 (신규)
    HIERARCHY_WEIGHT = 0.1       # 분류 계층 매칭 (0.3 → 0.1)
    DISPUTE_WEIGHT = 0.1         # 분쟁유형 매칭 (0.2 → 0.1)
    VECTOR_WEIGHT = 0.0          # 벡터 유사도 (0.1 → 0.0, 보조만)
    
    # 품목명 정확 매칭 보너스 (Phase 2 미세 조정)
    EXACT_ITEM_MATCH_BONUS = 2.0  # 정확 매칭 시 +2.0 고정 보너스 (3.0 → 2.0)
    
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
        query_embedding: Optional[List[float]] = None,
        top_k: int = 10
    ) -> List[CriteriaSearchResult]:
        """
        기준 검색
        
        Args:
            query: 원본 쿼리
            query_analysis: 쿼리 분석 결과
            query_embedding: 쿼리 임베딩 벡터 (선택)
            top_k: 반환할 최대 결과 수
        
        Returns:
            기준 검색 결과 리스트
        """
        self.connect_db()
        
        results = []
        
        # 1. 품목명 정확 매칭
        if query_analysis.extracted_items:
            item_results = self._item_name_search(
                query_analysis.extracted_items,
                query_analysis.dispute_types
            )
            results.extend(item_results)
        
        # 2. 분쟁유형 + 키워드 검색
        if query_analysis.dispute_types:
            dispute_results = self._dispute_type_search(
                query_analysis.dispute_types,
                query_analysis.keywords,
                top_k=top_k * 2
            )
            results.extend(dispute_results)
        
        # 3. 벡터 유사도 검색 (보완)
        if query_embedding:
            vector_results = self._vector_search(
                query_embedding,
                top_k=top_k
            )
            results.extend(vector_results)
        
        # 4. 중복 제거 및 점수 통합
        unique_results = self._deduplicate_and_score(results, query_analysis)
        
        # 5. 상위 K개 반환
        unique_results.sort(key=lambda x: x.final_score, reverse=True)
        return unique_results[:top_k]
    
    def _item_name_search(
        self,
        item_names: List[str],
        dispute_types: List[str]
    ) -> List[CriteriaSearchResult]:
        """
        품목명 정확 매칭 검색
        
        Args:
            item_names: 추출된 품목명 리스트
            dispute_types: 분쟁 유형 리스트
        
        Returns:
            검색 결과 리스트
        """
        results = []
        
        for item_name in item_names:
            # 품목명 또는 별칭(aliases)으로 검색
            sql = """
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.content,
                    d.metadata
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE 
                    (d.doc_type LIKE 'criteria%%' OR d.doc_type LIKE 'guideline%%')
                    AND c.drop = FALSE
                    AND (
                        d.metadata->>'item_name' ILIKE %s
                        OR jsonb_exists(d.metadata->'aliases', %s)
                        OR c.content ILIKE %s
                    )
                ORDER BY c.chunk_index
                LIMIT 10
            """
            
            search_pattern = f'%{item_name}%'
            
            self.cur.execute(sql, (search_pattern, item_name, search_pattern))
            rows = self.cur.fetchall()
            
            for row in rows:
                chunk_id, doc_id, content, metadata = row
                metadata = metadata or {}
                
                # 품목명 정확 매칭이므로 높은 점수
                item_match_score = 1.0 if metadata.get('item_name', '').lower() == item_name.lower() else 0.8
                
                # 분쟁유형 매칭 점수
                dispute_match_score = 0.0
                if dispute_types and metadata.get('dispute_type'):
                    if any(dt in metadata.get('dispute_type', '') for dt in dispute_types):
                        dispute_match_score = 1.0
                
                results.append(CriteriaSearchResult(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content=content,
                    item_name=metadata.get('item_name'),
                    category=metadata.get('category'),
                    industry=metadata.get('industry'),
                    item_group=metadata.get('item_group'),
                    dispute_type=metadata.get('dispute_type'),
                    item_match_score=item_match_score,
                    hierarchy_match_score=0.0,  # 나중에 계산
                    dispute_match_score=dispute_match_score,
                    vector_similarity=0.0,
                    final_score=0.0,
                    metadata=metadata
                ))
        
        return results
    
    def _dispute_type_search(
        self,
        dispute_types: List[str],
        keywords: List[str],
        top_k: int = 20
    ) -> List[CriteriaSearchResult]:
        """
        분쟁유형 + 키워드 검색
        
        Args:
            dispute_types: 분쟁 유형 리스트
            keywords: 키워드 리스트
            top_k: 반환할 최대 결과 수
        
        Returns:
            검색 결과 리스트
        """
        results = []
        
        # 분쟁유형이 포함된 청크 검색
        for dispute_type in dispute_types:
            sql = """
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.content,
                    d.metadata
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE 
                    (d.doc_type LIKE 'criteria%%' OR d.doc_type LIKE 'guideline%%')
                    AND c.drop = FALSE
                    AND (
                        d.metadata->>'dispute_type' ILIKE %s
                        OR c.content ILIKE %s
                    )
                ORDER BY c.importance_score DESC
                LIMIT %s
            """
            
            search_pattern = f'%{dispute_type}%'
            
            self.cur.execute(sql, (search_pattern, search_pattern, top_k))
            rows = self.cur.fetchall()
            
            for row in rows:
                chunk_id, doc_id, content, metadata = row
                metadata = metadata or {}
                
                results.append(CriteriaSearchResult(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content=content,
                    item_name=metadata.get('item_name'),
                    category=metadata.get('category'),
                    industry=metadata.get('industry'),
                    item_group=metadata.get('item_group'),
                    dispute_type=metadata.get('dispute_type'),
                    item_match_score=0.0,
                    hierarchy_match_score=0.0,
                    dispute_match_score=1.0,
                    vector_similarity=0.0,
                    final_score=0.0,
                    metadata=metadata
                ))
        
        return results
    
    def _vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[CriteriaSearchResult]:
        """
        벡터 유사도 검색
        
        Args:
            query_embedding: 쿼리 임베딩
            top_k: 반환할 최대 결과 수
        
        Returns:
            검색 결과 리스트
        """
        sql = """
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                d.metadata,
                1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                (d.doc_type LIKE 'criteria%%%%' OR d.doc_type LIKE 'guideline%%%%')
                AND c.drop = FALSE
                AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """
        
        self.cur.execute(sql, (query_embedding, query_embedding, top_k))
        rows = self.cur.fetchall()
        
        results = []
        for row in rows:
            chunk_id, doc_id, content, metadata, similarity = row
            metadata = metadata or {}
            
            results.append(CriteriaSearchResult(
                chunk_id=chunk_id,
                doc_id=doc_id,
                content=content,
                item_name=metadata.get('item_name'),
                category=metadata.get('category'),
                industry=metadata.get('industry'),
                item_group=metadata.get('item_group'),
                dispute_type=metadata.get('dispute_type'),
                item_match_score=0.0,
                hierarchy_match_score=0.0,
                dispute_match_score=0.0,
                vector_similarity=float(similarity),
                final_score=0.0,
                metadata=metadata
            ))
        
        return results
    
    def _calculate_keyword_bonus(
        self,
        content: str,
        keywords: List[str]
    ) -> float:
        """
        키워드 보너스 점수 계산 (Phase 2 신규)
        
        Criteria 특화 키워드에 높은 가중치 부여
        
        Args:
            content: 청크 내용
            keywords: 쿼리 키워드 리스트
        
        Returns:
            키워드 점수 (0~1)
        """
        # Criteria 특화 키워드 (높은 가중치)
        criteria_specific_keywords = [
            '품질보증', '보증기간', '보증', '기준',
            '무상수리', '무상교환', '무상',
            '부품보유', '부품보유기간', '부품',
            '내구연한', '내구', '사용기간',
            'A/S', '에이에스', '서비스',
            '해결기준', '분쟁해결', '조정기준',
            '환불', '교환', '수리', '반품'
        ]
        
        score = 0.0
        content_lower = content.lower()
        
        # 특화 키워드 매칭 (0.5점씩)
        for keyword in criteria_specific_keywords:
            if keyword.lower() in content_lower:
                score += 0.5
        
        # 일반 키워드 매칭 (0.2점씩)
        for keyword in keywords:
            if len(keyword) >= 2 and keyword.lower() in content_lower:
                score += 0.2
        
        return min(score, 1.0)  # 최대 1.0
    
    def _calculate_hierarchy_score(
        self,
        result: CriteriaSearchResult,
        query_analysis: QueryAnalysis
    ) -> float:
        """
        분류 계층 매칭 점수 계산
        
        카테고리 > 산업분류 > 품목그룹 계층 구조를 고려
        
        Args:
            result: 검색 결과
            query_analysis: 쿼리 분석 정보
        
        Returns:
            계층 매칭 점수 (0~1)
        """
        score = 0.0
        keywords_lower = [k.lower() for k in query_analysis.keywords]
        
        # 카테고리 매칭 (가장 상위)
        if result.category:
            # category가 리스트인 경우 처리
            category_str = ' '.join(result.category) if isinstance(result.category, list) else result.category
            if any(k in category_str.lower() for k in keywords_lower):
                score += 0.5
        
        # 산업분류 매칭 (중간)
        if result.industry:
            industry_str = ' '.join(result.industry) if isinstance(result.industry, list) else result.industry
            if any(k in industry_str.lower() for k in keywords_lower):
                score += 0.3
        
        # 품목그룹 매칭 (하위)
        if result.item_group:
            item_group_str = ' '.join(result.item_group) if isinstance(result.item_group, list) else result.item_group
            if any(k in item_group_str.lower() for k in keywords_lower):
                score += 0.2
        
        return min(score, 1.0)
    
    def _deduplicate_and_score(
        self,
        results: List[CriteriaSearchResult],
        query_analysis: QueryAnalysis
    ) -> List[CriteriaSearchResult]:
        """
        중복 제거 및 최종 점수 계산
        
        Args:
            results: 검색 결과 리스트
            query_analysis: 쿼리 분석 정보
        
        Returns:
            중복 제거 및 점수 계산된 결과 리스트
        """
        # chunk_id로 그룹화
        chunk_map = {}
        
        for result in results:
            chunk_id = result.chunk_id
            
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = result
            else:
                # 기존 결과와 점수 병합 (최대값 사용)
                existing = chunk_map[chunk_id]
                existing.item_match_score = max(
                    existing.item_match_score,
                    result.item_match_score
                )
                existing.dispute_match_score = max(
                    existing.dispute_match_score,
                    result.dispute_match_score
                )
                existing.vector_similarity = max(
                    existing.vector_similarity,
                    result.vector_similarity
                )
        
        # 계층 점수, 키워드 보너스 계산 및 최종 점수 계산 (Phase 2 개선)
        unique_results = []
        for result in chunk_map.values():
            # 1. 계층 점수 계산
            result.hierarchy_match_score = self._calculate_hierarchy_score(
                result, query_analysis
            )
            
            # 2. 키워드 보너스 계산 (Phase 2 신규)
            keyword_bonus = self._calculate_keyword_bonus(
                result.content,
                query_analysis.keywords
            )
            
            # 3. 기본 점수 계산
            base_score = (
                result.item_match_score * self.ITEM_MATCH_WEIGHT +
                keyword_bonus * self.KEYWORD_WEIGHT +
                result.hierarchy_match_score * self.HIERARCHY_WEIGHT +
                result.dispute_match_score * self.DISPUTE_WEIGHT +
                result.vector_similarity * self.VECTOR_WEIGHT
            )
            
            # 4. 품목명 정확 매칭 시 고정 보너스 +3.0 (Phase 2 핵심)
            if result.item_match_score >= 0.8:  # 정확 또는 근사 매칭
                base_score += self.EXACT_ITEM_MATCH_BONUS
            
            result.final_score = base_score
            unique_results.append(result)
        
        return unique_results
