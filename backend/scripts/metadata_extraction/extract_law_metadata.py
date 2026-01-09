#!/usr/bin/env python3
"""
    

  keywords, search_vector    DB 
"""

import json
import re
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path
import sys
from typing import List, Dict, Set
from collections import Counter

#   Python  
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


class LawMetadataExtractor:
    """  """
    
    #    
    LEGAL_TERMS = {
        '': 2.0, '': 2.0, '': 1.5, '': 1.5,
        '': 2.0, '': 1.8, '': 1.8, '': 1.8,
        '': 1.5, '': 1.5, '': 1.5, '': 1.5,
        '': 2.0, '': 1.8, '': 1.8, '': 1.8,
        '': 1.5, '': 1.5, '': 1.5,
        '': 1.3, '': 1.3, '': 1.3,
    }
    
    #  ( )
    STOPWORDS = {
        '', '', '', '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '',
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
    
    def extract_keywords(self, text: str, metadata: Dict) -> List[str]:
        """
          
        
        Args:
            text:  
            metadata:  
        
        Returns:
              
        """
        keywords = set()
        
        # 1.   
        if metadata.get('law_name'):
            keywords.add(metadata['law_name'])
        if metadata.get('article_no'):
            keywords.add(metadata['article_no'])
        if metadata.get('path'):
            keywords.add(metadata['path'])
        
        # 2.    ( )
        # , ,   
        text_clean = re.sub(r'[^\w\s-]', ' ', text)
        words = text_clean.split()
        
        #   
        word_freq = Counter()
        for word in words:
            word = word.strip()
            if len(word) >= 2 and word not in self.STOPWORDS:
                #    
                weight = self.LEGAL_TERMS.get(word, 1.0)
                word_freq[word] += weight
        
        # 3.    ( )
        top_keywords = [word for word, _ in word_freq.most_common(15)]
        keywords.update(top_keywords)
        
        # 4.     (N, N )
        article_patterns = re.findall(r'\d+', text)
        keywords.update(article_patterns[:5])  #  5
        
        return list(keywords)[:20]  #  20 
    
    def extract_metadata_for_law_docs(self, batch_size: int = 100):
        """
             
        
        Args:
            batch_size:  
        """
        print("\n     ...")
        
        #   
        try:
            self.cur.execute("""
                SELECT d.doc_id, d.title, d.metadata, c.content
                FROM documents d
                JOIN chunks c ON d.doc_id = c.doc_id
                WHERE d.doc_type = 'law'
                    AND d.keywords IS NULL
                    AND c.chunk_index = 0  --    
                ORDER BY d.doc_id
            """)
            
            law_docs = self.cur.fetchall()
        except Exception as e:
            print(f"    : {e}")
            return
        
        total = len(law_docs)
        
        if total == 0:
            print("     .")
            return
        
        print(f"  {total}   ")
        
        updates = []
        for idx, row in enumerate(law_docs, 1):
            try:
                if len(row) != 4:
                    print(f"    row  (: {len(row)})")
                    continue
                
                doc_id, title, metadata, content = row
                
                if idx % 100 == 0:
                    print(f"   : {idx}/{total} ({idx/total*100:.1f}%)")
                
                #  
                keywords = self.extract_keywords(content, metadata or {})
                
                updates.append((keywords, doc_id))
                
                #    
                if len(updates) >= batch_size:
                    self._update_keywords(updates)
                    updates = []
            except Exception as e:
                print(f"      (idx={idx}): {e}")
                continue
        
        #   
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
        """, updates)
        self.conn.commit()
    
    def calculate_chunk_importance(self):
        """
           
        
         :
        - article (): 1.5
        - paragraph (): 1.2
        - item (): 1.0
        """
        print("\n     ...")
        
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
        
        print(f"     : {updated}")
    
    def run(self):
        """  """
        try:
            self.connect_db()
            self.extract_metadata_for_law_docs()
            self.calculate_chunk_importance()
            
            #  
            self.cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE keywords IS NOT NULL) as with_keywords
                FROM documents
                WHERE doc_type = 'law'
            """)
            stats = self.cur.fetchone()
            
            print("\n" + "="*50)
            print("    ")
            print("="*50)
            print(f"    : {stats[0]}")
            print(f"    : {stats[1]}")
            print(f"  : {stats[1]/stats[0]*100:.1f}%" if stats[0] > 0 else "")
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
    
    extractor = LawMetadataExtractor(DB_CONFIG)
    extractor.run()
