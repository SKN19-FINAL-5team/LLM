#!/usr/bin/env python3
"""
법령 데이터 메타데이터 추출 스크립트

법령 데이터에서 keywords, search_vector 등의 메타데이터를 추출하여 DB에 저장
"""

import json
import re
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path
import sys
from typing import List, Dict, Set
from collections import Counter

# 부모 디렉토리를 Python 경로에 추가
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


class LawMetadataExtractor:
    """법령 메타데이터 추출기"""
    
    # 법률 용어 중요도 가중치
    LEGAL_TERMS = {
        '제': 2.0, '조': 2.0, '항': 1.5, '호': 1.5,
        '법률': 2.0, '규정': 1.8, '시행령': 1.8, '시행규칙': 1.8,
        '소비자': 1.5, '사업자': 1.5, '계약': 1.5, '책임': 1.5,
        '손해배상': 2.0, '환급': 1.8, '교환': 1.8, '반품': 1.8,
        '취소': 1.5, '해제': 1.5, '철회': 1.5,
        '권리': 1.3, '의무': 1.3, '금지': 1.3,
    }
    
    # 불용어 (제외할 단어)
    STOPWORDS = {
        '의', '가', '이', '은', '는', '을', '를', '에', '에서', '으로', '로',
        '과', '와', '및', '그', '저', '이것', '그것', '것',
        '등', '기타', '경우', '때', '수', '내', '중', '간',
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
    
    def extract_keywords(self, text: str, metadata: Dict) -> List[str]:
        """
        텍스트에서 키워드 추출
        
        Args:
            text: 청크 텍스트
            metadata: 문서 메타데이터
        
        Returns:
            추출된 키워드 리스트
        """
        keywords = set()
        
        # 1. 조문 정보 추가
        if metadata.get('law_name'):
            keywords.add(metadata['law_name'])
        if metadata.get('article_no'):
            keywords.add(metadata['article_no'])
        if metadata.get('path'):
            keywords.add(metadata['path'])
        
        # 2. 텍스트에서 단어 추출 (간단한 토큰화)
        # 한글, 숫자, 일부 특수문자만 유지
        text_clean = re.sub(r'[^\w\s가-힣]', ' ', text)
        words = text_clean.split()
        
        # 단어 빈도 계산
        word_freq = Counter()
        for word in words:
            word = word.strip()
            if len(word) >= 2 and word not in self.STOPWORDS:
                # 법률 용어에 가중치 적용
                weight = self.LEGAL_TERMS.get(word, 1.0)
                word_freq[word] += weight
        
        # 3. 상위 키워드 선택 (빈도 기준)
        top_keywords = [word for word, _ in word_freq.most_common(15)]
        keywords.update(top_keywords)
        
        # 4. 조문 번호 패턴 추출 (제N조, 제N항 등)
        article_patterns = re.findall(r'제\d+조', text)
        keywords.update(article_patterns[:5])  # 최대 5개
        
        return list(keywords)[:20]  # 최대 20개 키워드
    
    def extract_metadata_for_law_docs(self, batch_size: int = 100):
        """
        법령 문서들의 메타데이터 추출 및 업데이트
        
        Args:
            batch_size: 배치 크기
        """
        print("\n🔍 법령 문서 메타데이터 추출 시작...")
        
        # 법령 문서 조회
        try:
            self.cur.execute("""
                SELECT d.doc_id, d.title, d.metadata, c.content
                FROM documents d
                JOIN chunks c ON d.doc_id = c.doc_id
                WHERE d.doc_type = 'law'
                    AND d.keywords IS NULL
                    AND c.chunk_index = 0  -- 첫 번째 청크만 사용
                ORDER BY d.doc_id
            """)
            
            law_docs = self.cur.fetchall()
        except Exception as e:
            print(f"⚠️  쿼리 실행 오류: {e}")
            return
        
        total = len(law_docs)
        
        if total == 0:
            print("⚠️  처리할 법령 문서가 없습니다.")
            return
        
        print(f"📊 총 {total}건의 법령 문서 발견")
        
        updates = []
        for idx, row in enumerate(law_docs, 1):
            try:
                if len(row) != 4:
                    print(f"⚠️  예상치 못한 row 구조 (길이: {len(row)})")
                    continue
                
                doc_id, title, metadata, content = row
                
                if idx % 100 == 0:
                    print(f"  처리 중: {idx}/{total} ({idx/total*100:.1f}%)")
                
                # 키워드 추출
                keywords = self.extract_keywords(content, metadata or {})
                
                updates.append((keywords, doc_id))
                
                # 배치 크기에 도달하면 업데이트
                if len(updates) >= batch_size:
                    self._update_keywords(updates)
                    updates = []
            except Exception as e:
                print(f"⚠️  행 처리 중 오류 (idx={idx}): {e}")
                continue
        
        # 남은 업데이트 처리
        if updates:
            self._update_keywords(updates)
        
        print(f"✅ 법령 메타데이터 추출 완료: {total}건")
    
    def _update_keywords(self, updates: List[tuple]):
        """키워드 배치 업데이트"""
        execute_batch(self.cur, """
            UPDATE documents
            SET keywords = %s,
                updated_at = NOW()
            WHERE doc_id = %s
        """, updates)
        self.conn.commit()
    
    def calculate_chunk_importance(self):
        """
        법령 청크의 중요도 계산
        
        중요도 기준:
        - article (조): 1.5
        - paragraph (항): 1.2
        - item (호): 1.0
        """
        print("\n🔍 법령 청크 중요도 계산 시작...")
        
        self.cur.execute("""
            UPDATE chunks
            SET importance_score = CASE
                WHEN chunk_type = 'article' THEN 1.5
                WHEN chunk_type = 'paragraph' THEN 1.2
                WHEN chunk_type = 'item' THEN 1.0
                ELSE 1.0
            END
            WHERE doc_id IN (
                SELECT doc_id FROM documents WHERE doc_type = 'law'
            )
        """)
        
        updated = self.cur.rowcount
        self.conn.commit()
        
        print(f"✅ 법령 청크 중요도 계산 완료: {updated}건")
    
    def run(self):
        """전체 프로세스 실행"""
        try:
            self.connect_db()
            self.extract_metadata_for_law_docs()
            self.calculate_chunk_importance()
            
            # 통계 출력
            self.cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE keywords IS NOT NULL) as with_keywords
                FROM documents
                WHERE doc_type = 'law'
            """)
            stats = self.cur.fetchone()
            
            print("\n" + "="*50)
            print("📊 법령 메타데이터 추출 완료")
            print("="*50)
            print(f"  전체 법령 문서: {stats[0]}건")
            print(f"  키워드 추출 완료: {stats[1]}건")
            print(f"  완료율: {stats[1]/stats[0]*100:.1f}%" if stats[0] > 0 else "")
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
    print("법령 메타데이터 추출")
    print("="*50)
    
    extractor = LawMetadataExtractor(DB_CONFIG)
    extractor.run()
