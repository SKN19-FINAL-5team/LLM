#!/usr/bin/env python3
"""
    

 (, ,  )  
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


class CriteriaMetadataExtractor:
    """  """
    
    #   
    DISPUTE_TYPES = {
        '': 1.5, '': 1.5, '': 1.5,
        '': 1.3, '': 1.3, '': 1.3, '': 1.3,
        '': 1.2, '': 1.3, '': 1.3,
        '': 1.4, '': 1.4, '': 1.3,
        '': 1.2, '': 1.2, '': 1.3,
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
    
    def extract_keywords_from_criteria(self, content: str, metadata: Dict) -> List[str]:
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
            item_name = metadata.get('item_name') or metadata.get('item')
            if item_name:
                keywords.add(item_name)
            
            #  (aliases)
            aliases = metadata.get('aliases', [])
            if isinstance(aliases, list):
                keywords.update(aliases[:5])  #  5
            elif isinstance(aliases, str):
                try:
                    aliases_list = json.loads(aliases)
                    keywords.update(aliases_list[:5])
                except:
                    pass
            
            # 
            if metadata.get('category'):
                keywords.add(metadata['category'])
            
            #  
            if metadata.get('industry'):
                keywords.add(metadata['industry'])
            
            #  
            if metadata.get('item_group'):
                keywords.add(metadata['item_group'])
            
            #  
            dispute_type = metadata.get('dispute_type')
            if dispute_type:
                keywords.add(dispute_type)
        
        # 2.    ()
        # : ": XXX", "[] XXX" 
        item_patterns = re.findall(r'(?:|item)[:\s]+([-a-zA-Z0-9\s,]+)', content, re.IGNORECASE)
        for pattern in item_patterns[:3]:
            items = [item.strip() for item in pattern.split(',')]
            keywords.update(items[:5])
        
        # 3.    
        for dispute_keyword in self.DISPUTE_TYPES.keys():
            if dispute_keyword in content:
                keywords.add(dispute_keyword)
        
        return list(keywords)[:25]  #  25
    
    def extract_metadata_for_criteria_docs(self, batch_size: int = 100):
        """   """
        print("\n     ...")
        
        #    (doc_type 'criteria'  'guideline' )
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
            print(f"    : {e}")
            return
        
        total = len(criteria_docs)
        
        if total == 0:
            print("     .")
            return
        
        print(f"  {total}   ")
        
        updates = []
        for idx, row in enumerate(criteria_docs, 1):
            try:
                if len(row) != 4:
                    print(f"    row  (: {len(row)})")
                    continue
                
                doc_id, title, metadata, content = row
                
                if idx % 50 == 0:
                    print(f"   : {idx}/{total} ({idx/total*100:.1f}%)")
                
                keywords = self.extract_keywords_from_criteria(content, metadata or {})
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
        """, updates)
        self.conn.commit()
    
    def calculate_chunk_importance(self):
        """
           
        
         :
        - resolution_row (): 2.0  <-  
        - item_chunk (): 1.5
        - warranty/lifespan (/): 1.3
        - guideline (): 1.0
        """
        print("\n     ...")
        
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
        
        print(f"     : {updated}")
    
    def run(self):
        """  """
        try:
            self.connect_db()
            self.extract_metadata_for_criteria_docs()
            self.calculate_chunk_importance()
            
            #  
            self.cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE keywords IS NOT NULL) as with_keywords
                FROM documents
                WHERE doc_type LIKE 'criteria%' OR doc_type LIKE 'guideline%'
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
    
    extractor = CriteriaMetadataExtractor(DB_CONFIG)
    extractor.run()
