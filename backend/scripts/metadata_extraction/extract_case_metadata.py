#!/usr/bin/env python3
"""
사례 데이터 메타데이터 추출 스크립트

분쟁조정사례 및 피해구제사례에서 메타데이터 추출
"""

import json
import re
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path
import sys
from typing import List, Dict
from collections import Counter
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import os

# 환경 변수 로드
backend_dir = Path(__file__).parent.parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)

# DB 연결 정보
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'ddoksori'),
    'user': os.getenv('POSTGRES_USER', 'maroco'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}


class CaseMetadataExtractor:
    """사례 메타데이터 추출기"""
    
    # 사례 관련 중요 키워드
    CASE_KEYWORDS = {
        '소비자': 1.3, '사업자': 1.3, '판매자': 1.2, '구매자': 1.2,
        '분쟁': 1.5, '조정': 1.4, '중재': 1.3, '합의': 1.3,
        '환불': 1.5, '교환': 1.5, '수리': 1.4, '보상': 1.4,
        '하자': 1.4, '불량': 1.3, '결함': 1.3, '파손': 1.3,
        '계약': 1.3, '청약': 1.2, '승낙': 1.2, '해제': 1.3,
    }
    
    # Chunk Type별 중요도
    CHUNK_TYPE_IMPORTANCE = {
        'judgment': 2.0,           # 판단 - 가장 중요
        'decision': 2.0,           # 결정
        'parties_claim': 1.3,      # 당사자 주장
        'case_overview': 1.2,      # 사건 개요
        'qa_combined': 1.5,        # Q&A 결합
        'question': 1.0,           # 질문
        'answer': 1.8,             # 답변 - 중요
    }
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
        self.cur = None
    
    def connect_db(self):
        """DB 연결"""
        self.conn = psycopg2.connect(**self.db_config)
        self.cur = self.conn.cursor()
        print(f"✅ DB 연결 성공: {self.db_config['dbname']}")
    
    def close_db(self):
        """DB 연결 종료"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        print("✅ DB 연결 종료")
    
    def extract_keywords_from_case(self, content: str, metadata: Dict) -> List[str]:
        """
        사례 데이터에서 키워드 추출
        
        Args:
            content: 청크 텍스트
            metadata: 문서 메타데이터
        
        Returns:
            추출된 키워드 리스트
        """
        keywords = set()
        
        # 1. 메타데이터에서 정보 추출
        if metadata:
            # 사건 번호
            case_no = metadata.get('case_no') or metadata.get('case_sn')
            if case_no:
                keywords.add(f"사건번호:{case_no}")
            
            # 결정 날짜 (연도만)
            decision_date = metadata.get('decision_date')
            if decision_date:
                year = str(decision_date)[:4] if len(str(decision_date)) >= 4 else None
                if year and year.isdigit():
                    keywords.add(f"{year}년")
        
        # 2. 텍스트에서 핵심 단어 추출
        text_clean = re.sub(r'[^\w\s가-힣]', ' ', content)
        words = text_clean.split()
        
        word_freq = Counter()
        for word in words:
            word = word.strip()
            if len(word) >= 2:
                weight = self.CASE_KEYWORDS.get(word, 1.0)
                word_freq[word] += weight
        
        # 상위 키워드
        top_keywords = [word for word, _ in word_freq.most_common(10)]
        keywords.update(top_keywords)
        
        # 3. 특정 패턴 추출
        # 금액 패턴
        amounts = re.findall(r'\d+만?\s?원', content)
        if amounts:
            keywords.add('금액포함')
        
        # 날짜 패턴
        dates = re.findall(r'\d{4}[년.-]\s?\d{1,2}[월.-]\s?\d{1,2}일?', content)
        if dates:
            keywords.add('날짜포함')
        
        return list(keywords)[:20]  # 최대 20개
    
    def extract_metadata_for_case_docs(self, batch_size: int = 500):
        """사례 문서들의 메타데이터 추출"""
        print("\n🔍 사례 문서 메타데이터 추출 시작...")
        
        # 사례 문서 조회 (mediation_case, counsel_case, consumer_relief_case 등)
        try:
            self.cur.execute("""
                SELECT d.doc_id, d.title, d.metadata, c.content
                FROM documents d
                JOIN chunks c ON d.doc_id = c.doc_id
                WHERE (d.doc_type LIKE '%case%' OR d.doc_type LIKE '%mediation%' OR d.doc_type LIKE '%counsel%')
                    AND d.keywords IS NULL
                    AND c.chunk_index = 0
                ORDER BY d.doc_id
                LIMIT 10000  -- 한 번에 최대 10000건씩 처리
            """)
        except Exception as e:
            print(f"⚠️  쿼리 실행 오류: {e}")
            return
        
        try:
            case_docs = self.cur.fetchall()
        except Exception as e:
            print(f"⚠️  데이터 조회 오류: {e}")
            return
        
        total = len(case_docs)
        
        if total == 0:
            print("⚠️  처리할 사례 문서가 없습니다.")
            return
        
        print(f"📊 총 {total}건의 사례 문서 발견 (배치 처리)")
        
        updates = []
        for idx, row in enumerate(case_docs, 1):
            try:
                # 안전하게 언패킹
                if len(row) != 4:
                    print(f"⚠️  예상치 못한 row 구조 (길이: {len(row)}): {row[:2] if len(row) >= 2 else row}")
                    continue
                
                doc_id, title, metadata, content = row
                
                if idx % 1000 == 0:
                    print(f"  처리 중: {idx}/{total} ({idx/total*100:.1f}%)")
                
                keywords = self.extract_keywords_from_case(content, metadata or {})
                updates.append((keywords, doc_id))
                
                if len(updates) >= batch_size:
                    self._update_keywords(updates)
                    updates = []
            except Exception as e:
                print(f"⚠️  행 처리 중 오류 (idx={idx}): {e}")
                continue
        
        if updates:
            self._update_keywords(updates)
        
        print(f"✅ 사례 메타데이터 추출 완료: {total}건")
    
    def _update_keywords(self, updates: List[tuple]):
        """키워드 배치 업데이트"""
        execute_batch(self.cur, """
            UPDATE documents
            SET keywords = %s,
                updated_at = NOW()
            WHERE doc_id = %s
        """, updates, page_size=500)
        self.conn.commit()
    
    def calculate_chunk_importance(self):
        """
        사례 청크의 중요도 계산
        
        chunk_type에 따라 중요도 부여
        """
        print("\n🔍 사례 청크 중요도 계산 시작...")
        
        try:
            # 각 chunk_type별로 importance 설정
            updates = []
            for chunk_type, importance in self.CHUNK_TYPE_IMPORTANCE.items():
                updates.append((importance, chunk_type))
            
            execute_batch(self.cur, """
                UPDATE chunks
                SET importance_score = %s
                WHERE chunk_type = %s
                    AND doc_id IN (
                        SELECT doc_id FROM documents 
                        WHERE doc_type LIKE '%case%' OR doc_type LIKE '%mediation%' OR doc_type LIKE '%counsel%'
                    )
            """, updates)
            
            updated = self.cur.rowcount
            self.conn.commit()
            
            print(f"✅ 사례 청크 중요도 계산 완료: {updated}건")
        except Exception as e:
            print(f"⚠️  중요도 계산 중 오류: {e}")
            self.conn.rollback()
    
    def run(self):
        """전체 프로세스 실행"""
        try:
            self.connect_db()
            self.extract_metadata_for_case_docs()
            self.calculate_chunk_importance()
            
            # 통계 출력
            self.cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE keywords IS NOT NULL) as with_keywords
                FROM documents
                WHERE doc_type LIKE '%case%' OR doc_type LIKE '%mediation%' OR doc_type LIKE '%counsel%'
            """)
            stats = self.cur.fetchone()
            
            print("\n" + "="*50)
            print("📊 사례 메타데이터 추출 완료")
            print("="*50)
            print(f"  전체 사례 문서: {stats[0]}건")
            print(f"  키워드 추출 완료: {stats[1]}건")
            if stats[0] > 0:
                print(f"  완료율: {stats[1]/stats[0]*100:.1f}%")
            print("="*50)
            
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.close_db()


if __name__ == '__main__':
    print("="*50)
    print("사례 메타데이터 추출")
    print("="*50)
    
    extractor = CaseMetadataExtractor(DB_CONFIG)
    extractor.run()
