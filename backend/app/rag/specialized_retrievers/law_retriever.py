"""
Law Retriever Module
법령 전용 검색기 - 조문 정확 매칭 + 키워드 + 벡터 유사도 결합
"""

import psycopg2
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from ..query_analyzer import QueryAnalysis


@dataclass
class LawSearchResult:
    """법령 검색 결과"""
    chunk_id: str
    doc_id: str
    content: str
    law_name: str
    article_no: Optional[str]
    path: str
    exact_match_score: float      # 조문 정확 매칭 점수
    keyword_match_score: float    # 키워드 매칭 점수
    vector_similarity: float      # 벡터 유사도
    final_score: float            # 최종 점수
    metadata: Dict


class LawRetriever:
    """법령 전용 검색기"""
    
    # 가중치 설정
    EXACT_MATCH_WEIGHT = 0.5    # 조문 정확 매칭
    KEYWORD_WEIGHT = 0.3        # 키워드 매칭
    VECTOR_WEIGHT = 0.2         # 벡터 유사도
    
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
        top_k: int = 10,
        debug: bool = False
    ) -> List[LawSearchResult]:
        """
        법령 검색
        
        Args:
            query: 원본 쿼리
            query_analysis: 쿼리 분석 결과
            query_embedding: 쿼리 임베딩 벡터 (선택)
            top_k: 반환할 최대 결과 수
            debug: 디버깅 로그 출력 여부
        
        Returns:
            법령 검색 결과 리스트
        """
        self.connect_db()
        
        results = []
        
        # DEBUG: 추출된 정보 확인
        if debug:
            print(f"\n[Law Retriever DEBUG]")
            print(f"  Query: {query}")
            print(f"  - Extracted articles: {query_analysis.extracted_articles}")
            print(f"  - Law names: {query_analysis.law_names}")
            print(f"  - Keywords: {query_analysis.keywords[:5] if len(query_analysis.keywords) > 5 else query_analysis.keywords}")
            print(f"  - Has embedding: {query_embedding is not None}")
        
        # 1. 조문 정확 매칭 (최우선)
        if query_analysis.extracted_articles:
            exact_results = self._exact_article_search(
                query_analysis.extracted_articles,
                query_analysis.law_names
            )
            if debug:
                print(f"  - Exact match results: {len(exact_results)}")
            results.extend(exact_results)
        elif debug:
            print(f"  - Exact match: SKIPPED (no articles extracted)")
        
        # 2. 키워드 + 벡터 하이브리드 검색
        if query_embedding:
            hybrid_results = self._hybrid_search(
                query_embedding,
                query_analysis.keywords,
                query_analysis.law_names,
                top_k=top_k * 2,  # 넉넉하게 가져옴
                debug=debug
            )
            if debug:
                print(f"  - Hybrid search results: {len(hybrid_results)}")
            results.extend(hybrid_results)
        else:
            # 벡터 없을 때는 키워드만
            keyword_results = self._keyword_only_search(
                query_analysis.keywords,
                query_analysis.law_names,
                top_k=top_k * 2
            )
            if debug:
                print(f"  - Keyword-only search results: {len(keyword_results)}")
            results.extend(keyword_results)
        
        # 3. 중복 제거 및 점수 통합
        unique_results = self._deduplicate_and_score(results)
        
        if debug:
            print(f"  - Unique results after dedup: {len(unique_results)}")
            if unique_results:
                print(f"  - Top 3 scores: {[f'{r.final_score:.3f}' for r in unique_results[:3]]}")
                print(f"  - Top result law_name: {unique_results[0].law_name}")
            else:
                print(f"  - ❌ NO RESULTS RETURNED")
        
        # 4. 상위 K개 반환
        unique_results.sort(key=lambda x: x.final_score, reverse=True)
        return unique_results[:top_k]
    
    def _exact_article_search(
        self,
        articles: List[Dict],
        law_names: List[str]
    ) -> List[LawSearchResult]:
        """
        조문 정확 매칭 검색
        
        Args:
            articles: 추출된 조문 정보 리스트
            law_names: 추출된 법령명 리스트
        
        Returns:
            검색 결과 리스트
        """
        results = []
        
        for article_info in articles:
            law_name = article_info.get('law_name')
            article_no = article_info.get('article_no')
            
            # 법령명이 없으면 추출된 법령명 사용
            if not law_name and law_names:
                law_name = law_names[0]
            
            # SQL 쿼리 구성
            # 참고: DB metadata에 law_name, article_no가 없으므로
            # chunk_id 패턴과 content 기반으로 검색
            sql = """
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.content,
                    d.title AS law_name,
                    c.chunk_type,
                    d.metadata
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE 
                    d.doc_type = 'law'
                    AND c.drop = FALSE
            """
            
            params = []
            
            if law_name:
                # 법령명은 title 또는 content에서 찾기
                sql += " AND (d.title ILIKE %s OR c.content ILIKE %s)"
                params.append(f'%{law_name}%')
                params.append(f'%{law_name}%')
            
            if article_no:
                # 조문 번호는 chunk_id 패턴 또는 content에서 찾기
                # chunk_id 형식: statute:001706:001706|A750
                # 제750조 → A750
                article_num = article_no.replace('제', '').replace('조', '').strip()
                sql += """ AND (
                    c.chunk_id ILIKE %s 
                    OR c.content ILIKE %s
                    OR c.content ILIKE %s
                )"""
                params.append(f'%|A{article_num}%')   # chunk_id 패턴
                params.append(f'%{article_no}%')       # 제750조
                params.append(f'%{article_num}조%')    # 750조
            
            sql += " ORDER BY c.chunk_index LIMIT 5"
            
            self.cur.execute(sql, params)
            rows = self.cur.fetchall()
            
            for row in rows:
                chunk_id, doc_id, content, law_name_db, chunk_type, metadata = row
                
                # content에서 조문 번호 추출 (예: "민법 제750조")
                article_match = re.search(r'제\s*\d+\s*조', content)
                article_no_db = article_match.group(0) if article_match else None
                
                # path 생성 (law_name + article_no)
                path = f"{law_name_db} {article_no_db}" if article_no_db else law_name_db
                
                # 정확 매칭이므로 점수 최대
                results.append(LawSearchResult(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content=content,
                    law_name=law_name_db or '',
                    article_no=article_no_db,
                    path=path or '',
                    exact_match_score=1.0,
                    keyword_match_score=0.0,
                    vector_similarity=0.0,
                    final_score=0.0,  # 나중에 계산
                    metadata=metadata or {}
                ))
        
        return results
    
    def _hybrid_search(
        self,
        query_embedding: List[float],
        keywords: List[str],
        law_names: List[str],
        top_k: int = 20,
        debug: bool = False
    ) -> List[LawSearchResult]:
        """
        키워드 + 벡터 하이브리드 검색
        
        Args:
            query_embedding: 쿼리 임베딩
            keywords: 키워드 리스트
            law_names: 법령명 리스트
            top_k: 반환할 최대 결과 수
            debug: 디버깅 로그 출력 여부
        
        Returns:
            검색 결과 리스트
        """
        # 법령명이 있으면 직접 SQL로 법령명 필터 추가
        if law_names:
            if debug:
                print(f"    > Using law name filter: {law_names[0]}")
            
            # 법령명으로 필터링된 벡터 검색
            sql = """
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.chunk_type,
                    c.content,
                    d.title,
                    d.doc_type,
                    d.source_org,
                    d.category_path,
                    d.metadata,
                    1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE d.doc_type = 'law'
                  AND c.drop = FALSE
                  AND c.embedding IS NOT NULL
                  AND (1 - (c.embedding <=> %s::vector)) >= 0.2
                  AND (d.title ILIKE %s OR c.content ILIKE %s)
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
            """
            
            law_name_pattern = f'%{law_names[0]}%'
            self.cur.execute(sql, (
                query_embedding,
                query_embedding,
                law_name_pattern,
                law_name_pattern,
                query_embedding,
                top_k
            ))
            
            rows = self.cur.fetchall()
            
            if debug:
                print(f"    > Found {len(rows)} results with law name filter")
            
            results = []
            for row in rows:
                (chunk_id, doc_id, chunk_type, content, doc_title,
                 doc_type, source_org, category_path, metadata, similarity) = row
                
                metadata = metadata or {}
                
                # 키워드 매칭 점수 계산
                keyword_score = self._calculate_keyword_score(content, keywords)
                
                results.append(LawSearchResult(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content=content,
                    law_name=metadata.get('law_name', doc_title or ''),
                    article_no=metadata.get('article_no'),
                    path=metadata.get('path', ''),
                    exact_match_score=0.0,
                    keyword_match_score=keyword_score,
                    vector_similarity=similarity,
                    final_score=0.0,  # 나중에 재계산
                    metadata=metadata
                ))
            
            return results
        
        # 법령명 없을 때는 기존 hybrid_search_chunks 함수 사용
        sql = """
            SELECT * FROM hybrid_search_chunks(
                query_embedding := %s::vector,
                query_keywords := %s,
                doc_type_filter := 'law',
                chunk_type_filter := NULL,
                source_org_filter := NULL,
                vector_weight := %s,
                keyword_weight := %s,
                top_k := %s,
                min_similarity := 0.2
            )
        """
        
        # 법령 검색에서는 키워드 가중치를 높임
        vector_weight = 0.4
        keyword_weight = 0.6
        
        self.cur.execute(sql, (
            query_embedding,
            keywords,
            vector_weight,
            keyword_weight,
            top_k
        ))
        
        rows = self.cur.fetchall()
        
        if debug:
            print(f"    > Found {len(rows)} results with hybrid_search_chunks")
        
        results = []
        
        for row in rows:
            (chunk_id, doc_id, chunk_type, content, doc_title,
             doc_type, source_org, category_path,
             vector_score, keyword_score, final_score) = row
            
            # 메타데이터 조회
            self.cur.execute("""
                SELECT metadata FROM documents WHERE doc_id = %s
            """, (doc_id,))
            metadata_row = self.cur.fetchone()
            metadata = metadata_row[0] if metadata_row else {}
            
            results.append(LawSearchResult(
                chunk_id=chunk_id,
                doc_id=doc_id,
                content=content,
                law_name=metadata.get('law_name', ''),
                article_no=metadata.get('article_no'),
                path=metadata.get('path', ''),
                exact_match_score=0.0,
                keyword_match_score=keyword_score,
                vector_similarity=vector_score,
                final_score=0.0,  # 나중에 재계산
                metadata=metadata
            ))
        
        return results
    
    def _calculate_keyword_score(self, content: str, keywords: List[str]) -> float:
        """
        키워드 매칭 점수 계산
        
        Args:
            content: 청크 내용
            keywords: 키워드 리스트
        
        Returns:
            키워드 매칭 점수 (0~1)
        """
        if not keywords:
            return 0.0
        
        content_lower = content.lower()
        score = 0.0
        
        # 법률 용어 리스트
        legal_terms = [
            '청약철회', '손해배상', '계약해제', '환급', '위약금', '소멸시효',
            '무효', '취소', '해지', '위반', '책임', '의무', '권리', '금지',
            '허용', '제한', '규정', '조항', '법률', '법령', '시행령', '시행규칙'
        ]
        
        for keyword in keywords:
            if keyword.lower() in content_lower:
                # 법률 용어는 가중치 2배
                if any(lt in keyword for lt in legal_terms):
                    score += 2.0
                else:
                    score += 1.0
        
        # 정규화
        return min(score / len(keywords), 1.0)
    
    def _keyword_only_search(
        self,
        keywords: List[str],
        law_names: List[str],
        top_k: int = 20
    ) -> List[LawSearchResult]:
        """
        키워드만 사용한 검색 (벡터 없을 때)
        
        Args:
            keywords: 키워드 리스트
            law_names: 법령명 리스트
            top_k: 반환할 최대 결과 수
        
        Returns:
            검색 결과 리스트
        """
        if not keywords:
            return []
        
        # 키워드 매칭 점수 계산
        sql = """
            WITH keyword_matches AS (
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.content,
                    d.metadata,
                    (
                        SELECT COUNT(*)::FLOAT / %s
                        FROM unnest(%s::TEXT[]) kw
                        WHERE c.content ILIKE '%%' || kw || '%%'
                    ) AS keyword_score
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE 
                    d.doc_type = 'law'
                    AND c.drop = FALSE
            )
            SELECT *
            FROM keyword_matches
            WHERE keyword_score > 0
            ORDER BY keyword_score DESC
            LIMIT %s
        """
        
        self.cur.execute(sql, (len(keywords), keywords, top_k))
        rows = self.cur.fetchall()
        
        results = []
        for row in rows:
            chunk_id, doc_id, content, metadata, keyword_score = row
            metadata = metadata or {}
            
            results.append(LawSearchResult(
                chunk_id=chunk_id,
                doc_id=doc_id,
                content=content,
                law_name=metadata.get('law_name', ''),
                article_no=metadata.get('article_no'),
                path=metadata.get('path', ''),
                exact_match_score=0.0,
                keyword_match_score=keyword_score,
                vector_similarity=0.0,
                final_score=0.0,
                metadata=metadata
            ))
        
        return results
    
    def _deduplicate_and_score(
        self,
        results: List[LawSearchResult]
    ) -> List[LawSearchResult]:
        """
        중복 제거 및 최종 점수 계산
        
        Args:
            results: 검색 결과 리스트
        
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
                existing.exact_match_score = max(
                    existing.exact_match_score,
                    result.exact_match_score
                )
                existing.keyword_match_score = max(
                    existing.keyword_match_score,
                    result.keyword_match_score
                )
                existing.vector_similarity = max(
                    existing.vector_similarity,
                    result.vector_similarity
                )
        
        # 최종 점수 계산
        unique_results = []
        for result in chunk_map.values():
            result.final_score = (
                result.exact_match_score * self.EXACT_MATCH_WEIGHT +
                result.keyword_match_score * self.KEYWORD_WEIGHT +
                result.vector_similarity * self.VECTOR_WEIGHT
            )
            unique_results.append(result)
        
        return unique_results
