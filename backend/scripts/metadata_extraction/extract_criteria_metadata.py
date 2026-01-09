#!/usr/bin/env python3
"""
기준 데이터 메타데이터 추출 스크립트

기준 데이터(품목, 분쟁해결기준, 보증기간 등)에서 메타데이터 추출
"""

import json
import re
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path
import sys
from typing import List, Dict

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


class CriteriaMetadataExtractor:
    """기준 메타데이터 추출기"""
    
    # 분쟁 유형 키워드
    DISPUTE_TYPES = {
        '환불': 1.5, '교환': 1.5, '수리': 1.5,
        '부패': 1.3, '변질': 1.3, '파손': 1.3, '불량': 1.3,
        '지연': 1.2, '미배송': 1.3, '오배송': 1.3,
        '하자': 1.4, '결함': 1.4, '오작동': 1.3,
        '취소': 1.2, '철회': 1.2, '반품': 1.3,
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
    
    def extract_keywords_from_criteria(self, content: str, metadata: Dict) -> List[str]:
        """
        기준 데이터에서 키워드 추출
        
        Args:
            content: 청크 텍스트
            metadata: 문서 메타데이터
        
        Returns:
            추출된 키워드 리스트
        """
        keywords = set()
        
        # 1. 메타데이터에서 구조화된 정보 추출
        if metadata:
            # 품목명
            item_name = metadata.get('item_name') or metadata.get('item')
            if item_name:
                keywords.add(item_name)
            
            # 별칭 (aliases)
            aliases = metadata.get('aliases', [])
            if isinstance(aliases, list):
                keywords.update(aliases[:5])  # 최대 5개
            elif isinstance(aliases, str):
                try:
                    aliases_list = json.loads(aliases)
                    keywords.update(aliases_list[:5])
                except:
                    pass
            
            # 카테고리
            if metadata.get('category'):
                keywords.add(metadata['category'])
            
            # 산업 분류
            if metadata.get('industry'):
                keywords.add(metadata['industry'])
            
            # 품목 그룹
            if metadata.get('item_group'):
                keywords.add(metadata['item_group'])
            
            # 분쟁 유형
            dispute_type = metadata.get('dispute_type')
            if dispute_type:
                keywords.add(dispute_type)
        
        # 2. 텍스트에서 품목명 추출 (정규식)
        # 패턴: "품목: XXX", "[품목] XXX" 등
        item_patterns = re.findall(r'(?:품목|item)[:\s]+([가-힣a-zA-Z0-9\s,]+)', content, re.IGNORECASE)
        for pattern in item_patterns[:3]:
            items = [item.strip() for item in pattern.split(',')]
            keywords.update(items[:5])
        
        # 3. 분쟁 유형 키워드 검출
        for dispute_keyword in self.DISPUTE_TYPES.keys():
            if dispute_keyword in content:
                keywords.add(dispute_keyword)
        
        return list(keywords)[:25]  # 최대 25개
    
    def extract_metadata_for_criteria_docs(self, batch_size: int = 100):
        """기준 문서들의 메타데이터 추출"""
        print("\n🔍 기준 문서 메타데이터 추출 시작...")
        
        # 기준 문서 조회 (doc_type이 'criteria'로 시작하거나 'guideline'로 시작)
        try:
            self.cur.execute("""
                SELECT d.doc_id, d.title, d.metadata, c.content
                FROM documents d
                JOIN chunks c ON d.doc_id = c.doc_id
                WHERE (d.doc_type LIKE 'criteria%' OR d.doc_type LIKE 'guideline%')
                    AND d.keywords IS NULL
                    AND c.chunk_index = 0
                ORDER BY d.doc_id
            """)
            
            criteria_docs = self.cur.fetchall()
        except Exception as e:
            print(f"⚠️  쿼리 실행 오류: {e}")
            return
        
        total = len(criteria_docs)
        
        if total == 0:
            print("⚠️  처리할 기준 문서가 없습니다.")
            return
        
        print(f"📊 총 {total}건의 기준 문서 발견")
        
        updates = []
        for idx, row in enumerate(criteria_docs, 1):
            try:
                if len(row) != 4:
                    print(f"⚠️  예상치 못한 row 구조 (길이: {len(row)})")
                    continue
                
                doc_id, title, metadata, content = row
                
                if idx % 50 == 0:
                    print(f"  처리 중: {idx}/{total} ({idx/total*100:.1f}%)")
                
                keywords = self.extract_keywords_from_criteria(content, metadata or {})
                updates.append((keywords, doc_id))
                
                if len(updates) >= batch_size:
                    self._update_keywords(updates)
                    updates = []
            except Exception as e:
                print(f"⚠️  행 처리 중 오류 (idx={idx}): {e}")
                continue
        
        if updates:
            self._update_keywords(updates)
        
        print(f"✅ 기준 메타데이터 추출 완료: {total}건")
    
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
        기준 청크의 중요도 계산
        
        중요도 기준:
        - resolution_row (해결기준): 2.0  <- 가장 중요
        - item_chunk (품목): 1.5
        - warranty/lifespan (보증/내용연수): 1.3
        - guideline (가이드라인): 1.0
        """
        print("\n🔍 기준 청크 중요도 계산 시작...")
        
        self.cur.execute("""
            UPDATE chunks
            SET importance_score = CASE
                WHEN chunk_type = 'resolution_row' THEN 2.0
                WHEN chunk_type LIKE '%item%' THEN 1.5
                WHEN chunk_type LIKE '%warranty%' OR chunk_type LIKE '%lifespan%' THEN 1.3
                WHEN chunk_type LIKE '%guideline%' THEN 1.0
                ELSE 1.0
            END
            WHERE doc_id IN (
                SELECT doc_id FROM documents 
                WHERE doc_type LIKE 'criteria%' OR doc_type LIKE 'guideline%'
            )
        """)
        
        updated = self.cur.rowcount
        self.conn.commit()
        
        print(f"✅ 기준 청크 중요도 계산 완료: {updated}건")
    
    def run(self):
        """전체 프로세스 실행"""
        try:
            self.connect_db()
            self.extract_metadata_for_criteria_docs()
            self.calculate_chunk_importance()
            
            # 통계 출력
            self.cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE keywords IS NOT NULL) as with_keywords
                FROM documents
                WHERE doc_type LIKE 'criteria%' OR doc_type LIKE 'guideline%'
            """)
            stats = self.cur.fetchone()
            
            print("\n" + "="*50)
            print("📊 기준 메타데이터 추출 완료")
            print("="*50)
            print(f"  전체 기준 문서: {stats[0]}건")
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
    print("기준 메타데이터 추출")
    print("="*50)
    
    extractor = CriteriaMetadataExtractor(DB_CONFIG)
    extractor.run()
