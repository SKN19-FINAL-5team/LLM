#!/usr/bin/env python3
"""
    

    
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

#   
backend_dir = Path(__file__).parent.parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)

# DB  
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'ddoksori'),
    'user': os.getenv('POSTGRES_USER', 'maroco'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}


class CaseMetadataExtractor:
    """  """
    
    #    
    CASE_KEYWORDS = {
        '': 1.3, '': 1.3, '': 1.2, '': 1.2,
        '': 1.5, '': 1.4, '': 1.3, '': 1.3,
        '': 1.5, '': 1.5, '': 1.4, '': 1.4,
        '': 1.4, '': 1.3, '': 1.3, '': 1.3,
        '': 1.3, '': 1.2, '': 1.2, '': 1.3,
    }
    
    # Chunk Type 
    CHUNK_TYPE_IMPORTANCE = {
        'judgment': 2.0,           #  -  
        'decision': 2.0,           # 
        'parties_claim': 1.3,      #  
        'case_overview': 1.2,      #  
        'qa_combined': 1.5,        # Q&A 
        'question': 1.0,           # 
        'answer': 1.8,             #  - 
    }
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
        self.cur = None
    
    def connect_db(self):
        """DB """
        self.conn = psycopg2.connect(**self.db_config)
        self.cur = self.conn.cursor()
        print(f" DB  : {self.db_config['dbname']}")
    
    def close_db(self):
        """DB  """
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        print(" DB  ")
    
    def extract_keywords_from_case(self, content: str, metadata: Dict) -> List[str]:
        """
           
        
        Args:
            content:  
            metadata:  
        
        Returns:
              
        """
        keywords = set()
        
        # 1.   
        if metadata:
            #  
            case_no = metadata.get('case_no') or metadata.get('case_sn')
            if case_no:
                keywords.add(f":{case_no}")
            
            #   ()
            decision_date = metadata.get('decision_date')
            if decision_date:
                year = str(decision_date)[:4] if len(str(decision_date)) >= 4 else None
                if year and year.isdigit():
                    keywords.add(f"{year}")
        
        # 2.    
        text_clean = re.sub(r'[^\w\s-]', ' ', content)
        words = text_clean.split()
        
        word_freq = Counter()
        for word in words:
            word = word.strip()
            if len(word) >= 2:
                weight = self.CASE_KEYWORDS.get(word, 1.0)
                word_freq[word] += weight
        
        #  
        top_keywords = [word for word, _ in word_freq.most_common(10)]
        keywords.update(top_keywords)
        
        # 3.   
        #  
        amounts = re.findall(r'\d+?\s?', content)
        if amounts:
            keywords.add('')
        
        #  
        dates = re.findall(r'\d{4}[.-]\s?\d{1,2}[.-]\s?\d{1,2}?', content)
        if dates:
            keywords.add('')
        
        return list(keywords)[:20]  #  20
    
    def extract_metadata_for_case_docs(self, batch_size: int = 500):
        """   """
        print("\n     ...")
        
        #    (mediation_case, counsel_case, consumer_relief_case )
        try:
            self.cur.execute("""
                SELECT d.doc_id, d.title, d.metadata, c.content
                FROM documents d
                JOIN chunks c ON d.doc_id = c.doc_id
                WHERE (d.doc_type LIKE '%case%' OR d.doc_type LIKE '%mediation%' OR d.doc_type LIKE '%counsel%')
                    AND d.keywords IS NULL
                    AND c.chunk_index = 0
                ORDER BY d.doc_id
                LIMIT 10000  --    10000 
            """)
        except Exception as e:
            print(f"    : {e}")
            return
        
        try:
            case_docs = self.cur.fetchall()
        except Exception as e:
            print(f"    : {e}")
            return
        
        total = len(case_docs)
        
        if total == 0:
            print("     .")
            return
        
        print(f"  {total}    ( )")
        
        updates = []
        for idx, row in enumerate(case_docs, 1):
            try:
                #  
                if len(row) != 4:
                    print(f"    row  (: {len(row)}): {row[:2] if len(row) >= 2 else row}")
                    continue
                
                doc_id, title, metadata, content = row
                
                if idx % 1000 == 0:
                    print(f"   : {idx}/{total} ({idx/total*100:.1f}%)")
                
                keywords = self.extract_keywords_from_case(content, metadata or {})
                updates.append((keywords, doc_id))
                
                if len(updates) >= batch_size:
                    self._update_keywords(updates)
                    updates = []
            except Exception as e:
                print(f"      (idx={idx}): {e}")
                continue
        
        if updates:
            self._update_keywords(updates)
        
        print(f"    : {total}")
    
    def _update_keywords(self, updates: List[tuple]):
        """  """
        execute_batch(self.cur, """
            UPDATE documents
            SET keywords = %s,
                updated_at = NOW()
            WHERE doc_id = %s
        """, updates, page_size=500)
        self.conn.commit()
    
    def calculate_chunk_importance(self):
        """
           
        
        chunk_type   
        """
        print("\n     ...")
        
        try:
            #  chunk_type importance 
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
            
            print(f"     : {updated}")
        except Exception as e:
            print(f"     : {e}")
            self.conn.rollback()
    
    def run(self):
        """  """
        try:
            self.connect_db()
            self.extract_metadata_for_case_docs()
            self.calculate_chunk_importance()
            
            #  
            self.cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE keywords IS NOT NULL) as with_keywords
                FROM documents
                WHERE doc_type LIKE '%case%' OR doc_type LIKE '%mediation%' OR doc_type LIKE '%counsel%'
            """)
            stats = self.cur.fetchone()
            
            print("\n" + "="*50)
            print("    ")
            print("="*50)
            print(f"    : {stats[0]}")
            print(f"    : {stats[1]}")
            if stats[0] > 0:
                print(f"  : {stats[1]/stats[0]*100:.1f}%")
            print("="*50)
            
        except Exception as e:
            print(f"\n  : {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.close_db()


if __name__ == '__main__':
    print("="*50)
    print("  ")
    print("="*50)
    
    extractor = CaseMetadataExtractor(DB_CONFIG)
    extractor.run()
