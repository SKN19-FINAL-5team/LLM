#!/usr/bin/env python3
"""
  Golden Set  

    
    golden set JSON  
"""

import os
import sys
import json
import psycopg2
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv
import argparse
from datetime import datetime
import re

#    
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'backend'))

from app.rag import VectorRetriever

load_dotenv()


class CriteriaGoldenSetGenerator:
    """  Golden Set """
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
        self.retriever = VectorRetriever(db_config)
    
    def connect_db(self):
        """ """
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def close_db(self):
        """  """
        if self.conn:
            self.conn.close()
        self.retriever.close()
    
    def extract_query_from_chunk(self, content: str, item_name: str = None) -> str:
        """
             
        
        Args:
            content:  
            item_name:  ()
        
        Returns:
              
        """
        query_parts = []
        
        #   
        if item_name:
            query_parts.append(item_name)
        
        #    
        content_clean = content.strip()
        
        #   
        product_keywords = ['', '', '', 'TV', '', '', '', 
                          '', '', '', '', '', '']
        found_products = [p for p in product_keywords if p in content_clean]
        if found_products:
            query_parts.extend(found_products[:2])
        
        #   
        criteria_keywords = ['', '', '', '', '', '', '']
        found_criteria = [k for k in criteria_keywords if k in content_clean]
        if found_criteria:
            query_parts.extend(found_criteria[:2])
        
        #   
        keywords = re.findall(r'[-]{2,4}', content_clean[:200])
        keywords = [k for k in keywords if len(k) >= 2][:3]
        
        if not query_parts and keywords:
            query_parts.extend(keywords)
        
        query = ' '.join(query_parts) if query_parts else content_clean[:50]
        return query.strip()
    
    def find_related_chunks(self, query: str, source_chunk_id: str, top_k: int = 10) -> List[str]:
        """
            (  )
        
        Args:
            query:  
            source_chunk_id:   ID ()
            top_k:    
        
        Returns:
              ID 
        """
        try:
            #     
            results = self.retriever.search(query=query, top_k=top_k * 2)
            
            # doc_type 'criteria_'     source_chunk_id 
            related_chunk_ids = []
            for result in results:
                source = result.get('source', '')
                if source.startswith('criteria_') and result.get('chunk_uid') != source_chunk_id:
                    related_chunk_ids.append(result.get('chunk_uid'))
                    if len(related_chunk_ids) >= top_k:
                        break
            
            return related_chunk_ids
        except Exception as e:
            print(f"       : {e}")
            return []
    
    def generate_golden_set(self, num_samples: int = 20) -> List[Dict]:
        """
        Golden Set 
        
        Args:
            num_samples:   
        
        Returns:
            Golden set 
        """
        self.connect_db()
        
        print(f"\n   Golden Set ")
        print(f" : {num_samples}")
        print("=" * 80)
        
        #    
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                c.chunk_type,
                d.title,
                d.metadata->>'item' as item_name,
                d.metadata->>'item_category' as item_category,
                d.doc_type
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type LIKE 'criteria_%'
                AND c.drop = FALSE
                AND c.embedding IS NOT NULL
                AND c.content IS NOT NULL
                AND LENGTH(c.content) > 50
            ORDER BY RANDOM()
            LIMIT %s
        """, (num_samples,))
        
        samples = cur.fetchall()
        cur.close()
        
        if not samples:
            print("     .")
            return []
        
        print(f" {len(samples)}   ")
        
        golden_set = []
        
        for idx, (chunk_id, doc_id, content, chunk_type, title, item_name, item_category, doc_type) in enumerate(samples, 1):
            print(f"\n[{idx}/{len(samples)}]  : {chunk_id[:50]}...")
            
            #  
            query = self.extract_query_from_chunk(content, item_name)
            print(f"   : {query}")
            
            #   
            related_chunk_ids = self.find_related_chunks(query, chunk_id, top_k=5)
            print(f"   : {len(related_chunk_ids)}")
            
            #   
            all_chunk_ids = [chunk_id] + related_chunk_ids
            all_doc_ids = [doc_id]
            
            #   ID 
            for rel_chunk_id in related_chunk_ids:
                cur = self.conn.cursor()
                cur.execute("SELECT doc_id FROM chunks WHERE chunk_id = %s", (rel_chunk_id,))
                rel_doc = cur.fetchone()
                cur.close()
                if rel_doc and rel_doc[0] not in all_doc_ids:
                    all_doc_ids.append(rel_doc[0])
            
            golden_item = {
                "query": query,
                "expected_chunk_ids": all_chunk_ids[:10],  #  10
                "expected_doc_ids": all_doc_ids[:5],  #  5
                "metadata": {
                    "source_chunk_id": chunk_id,
                    "source_doc_id": doc_id,
                    "chunk_type": chunk_type,
                    "doc_type": doc_type,
                    "item_name": item_name,
                    "item_category": item_category,
                    "title": title,
                    "content_preview": content[:200] if content else None
                }
            }
            
            golden_set.append(golden_item)
        
        return golden_set
    
    def save_golden_set(self, golden_set: List[Dict], output_file: Path):
        """Golden Set JSON  """
        output_data = {
            "metadata": {
                "data_type": "criteria",
                "doc_type": "criteria_item,criteria_resolution,criteria_warranty,criteria_lifespan",
                "generated_at": datetime.now().isoformat(),
                "num_samples": len(golden_set)
            },
            "golden_set": golden_set
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n Golden Set  : {output_file}")
        print(f"    {len(golden_set)} ")


def main():
    """ """
    parser = argparse.ArgumentParser(description='  Golden Set ')
    parser.add_argument('--num-samples', type=int, default=20,
                       help='   (: 20)')
    parser.add_argument('--output', type=str, default='golden_set_criteria.json',
                       help='   (: golden_set_criteria.json)')
    args = parser.parse_args()
    
    #    
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    #   
    script_dir = Path(__file__).parent
    output_file = script_dir / args.output
    
    # Golden Set 
    generator = CriteriaGoldenSetGenerator(db_config)
    
    try:
        golden_set = generator.generate_golden_set(num_samples=args.num_samples)
        
        if golden_set:
            generator.save_golden_set(golden_set, output_file)
        else:
            print(" Golden Set  ")
            sys.exit(1)
    
    except Exception as e:
        print(f"  : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        generator.close_db()


if __name__ == "__main__":
    main()
