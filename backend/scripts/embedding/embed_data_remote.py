#!/usr/bin/env python3
"""
   ( API )

 JSON  PostgreSQL + pgvector 
RunPod GPU   

Features:
-  JSON  
- documents, chunks  
- drop=True   
-    ( content  )
-    (   )
"""

import os
import json
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from tqdm import tqdm
from typing import List, Dict, Tuple
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import numpy as np

load_dotenv()

#      
SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/embedding/
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # ddoksori_demo/
DATA_DIR = PROJECT_ROOT / "backend" / "data"


class EmbeddingPipeline:
    """  ( -   )"""
    
    def __init__(self, db_config: Dict[str, str], embed_api_url: str, load_only: bool = False):
        """
        Args:
            db_config: PostgreSQL  
            embed_api_url:   API URL
            load_only: True     
        """
        self.db_config = db_config
        self.embed_api_url = embed_api_url
        self.load_only = load_only
        self.conn = None
        self.batch_size = 32  #   
        
        # 
        self.stats = {
            'documents': 0,
            'chunks': 0,
            'chunks_skipped': 0,  # drop=True
            'chunks_embedded': 0,
            'chunks_empty': 0,  #  content
            'chunks_preprocessed': 0,  #   ()
            'low_quality_texts': 0,  #   ( , )
            'low_quality_embeddings': 0,  #  
            'quality_warnings': [],  #   
            'errors': []
        }
        
        # API   (load_only    )
        self.api_available = self._test_api_connection(skip_if_failed=load_only)
    
    def _test_api_connection(self, skip_if_failed=False):
        """ API  """
        print(f"\n  API  : {self.embed_api_url}")
        try:
            base_url = self.embed_api_url.rsplit('/', 1)[0]
            response = requests.get(base_url, timeout=10)
            response.raise_for_status()
            print(f" API  : {response.json()}")
            return True
        except requests.exceptions.RequestException as e:
            if skip_if_failed:
                print(f"  API   (  ): {e}")
                print("       .")
                return False
            print(f" API  : {e}")
            print("\n :")
            print("1. SSH : ssh -L 8001:localhost:8000 [user]@[host] -p [port]")
            print("2. RunPod : uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000")
            raise
    
    def preprocess_text(self, text: str) -> str:
        """
            ()
        
         :
        1.   
        2.    (3  → 2)
        3.  
        4.   
        
        Args:
            text:  
            
        Returns:
             
        """
        if not text:
            return text
        
        import re
        
        # 1.   
        text = re.sub(r' +', ' ', text)
        
        # 2.    (3  → 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 3.  
        text = text.replace('\t', ' ')
        
        # 4.    
        text = text.replace('\u3000', ' ')  #  
        text = text.replace('\xa0', ' ')  # Non-breaking space
        
        # 5.   
        text = text.strip()
        
        return text
    
    def validate_text_quality(self, text: str) -> tuple[bool, str]:
        """
            ()
        
              
           
        
         :
        1.   (20 )
        2.     (30% )
        3.    (  80%   )
        4.   (URL,  )
        
        Args:
            text:  
            
        Returns:
            (is_valid, reason):   
        """
        if not text or not text.strip():
            return False, " "
        
        text = text.strip()
        
        # 1.   
        if len(text) < 20:
            return False, f"  ({len(text)})"
        
        # 2.    
        import re
        meaningful_chars = re.findall(r'[-a-zA-Z0-9]', text)
        if len(meaningful_chars) / len(text) < 0.3:
            return False, f"    ({len(meaningful_chars)}/{len(text)})"
        
        # 3.    
        from collections import Counter
        char_counts = Counter(text)
        most_common_char, most_common_count = char_counts.most_common(1)[0]
        if most_common_count / len(text) > 0.8:
            return False, f"   ('{most_common_char}' {most_common_count})"
        
        # 4. URL 
        urls = re.findall(r'https?://[^\s]+', text)
        url_length = sum(len(url) for url in urls)
        if url_length / len(text) > 0.8:
            return False, "URL "
        
        # 5.  
        digits = re.findall(r'\d', text)
        if len(digits) / len(text) > 0.9:
            return False, " "
        
        return True, ""
    
    def connect_db(self):
        """PostgreSQL """
        if self.conn:
            return
        
        print("\n  ...")
        self.conn = psycopg2.connect(**self.db_config)
        
        # pgvector   (vector   )
        try:
            from pgvector.psycopg2 import register_vector
            register_vector(self.conn)
        except ImportError:
            print("    pgvector  . vector   .")
        
        print("   ")
    
    def close_db(self):
        """DB  """
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def load_json_file(self, file_path: Path) -> Dict:
        """JSON  """
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def insert_documents(self, documents: List[Dict]):
        """documents   """
        if not documents:
            return
        
        print(f"\n  : {len(documents)}")
        
        with self.conn.cursor() as cur:
            insert_query = """
                INSERT INTO documents (
                    doc_id, doc_type, title, source_org, 
                    category_path, url, metadata
                )
                VALUES %s
                ON CONFLICT (doc_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    metadata = EXCLUDED.metadata
            """
            
            values = [
                (
                    doc['doc_id'],
                    doc['doc_type'],
                    doc['title'],
                    doc.get('source_org'),
                    doc.get('category_path'),
                    doc.get('url'),
                    json.dumps(doc.get('metadata', {}))
                )
                for doc in documents
            ]
            
            execute_values(cur, insert_query, values)
            self.conn.commit()
            self.stats['documents'] += len(documents)
            print(f" {len(documents)}   ")
    
    def insert_chunks(self, doc_id: str, chunks: List[Dict]) -> List[Tuple[str, str]]:
        """
        chunks    ( -     )
        
        Returns:
            List[(chunk_id, content)]:     
        """
        if not chunks:
            return []
        
        # drop=True  
        valid_chunks = [c for c in chunks if not c.get('drop', False)]
        skipped = len(chunks) - len(valid_chunks)
        
        if skipped > 0:
            self.stats['chunks_skipped'] += skipped
        
        if not valid_chunks:
            return []
        
        with self.conn.cursor() as cur:
            insert_query = """
                INSERT INTO chunks (
                    chunk_id, doc_id, chunk_index, chunk_total,
                    chunk_type, content, content_length, drop
                )
                VALUES %s
                ON CONFLICT (chunk_id) DO UPDATE SET
                    content = EXCLUDED.content
            """
            
            values = [
                (
                    chunk['chunk_id'],
                    doc_id,
                    chunk['chunk_index'],
                    chunk['chunk_total'],
                    chunk['chunk_type'],
                    chunk['content'],
                    chunk['content_length'],
                    chunk.get('drop', False)
                )
                for chunk in valid_chunks
            ]
            
            execute_values(cur, insert_query, values)
            self.conn.commit()
            self.stats['chunks'] += len(valid_chunks)
        
        #      (    )
        chunks_to_embed = []
        
        for chunk in valid_chunks:
            content = chunk['content']
            
            #  content 
            if not content or not content.strip():
                self.stats['chunks_empty'] += 1
                continue
            
            #   ()
            preprocessed_content = self.preprocess_text(content)
            self.stats['chunks_preprocessed'] += 1
            
            #     ()
            is_valid, reason = self.validate_text_quality(preprocessed_content)
            
            if not is_valid:
                #     
                self.stats['low_quality_texts'] += 1
                warning_msg = (
                    f"  : {chunk['chunk_id']}\n"
                    f"  : {reason}\n"
                    f"   : {len(content)}\n"
                    f"  : {content[:100]}..."
                )
                self.stats['quality_warnings'].append(warning_msg)
                
                #  5 
                if self.stats['low_quality_texts'] <= 5:
                    print(f"\n  {warning_msg}")
                
                continue
            
            chunks_to_embed.append((chunk['chunk_id'], preprocessed_content))
        
        return chunks_to_embed
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
         API   
        
        Args:
            texts:   
            
        Returns:
              
        """
        try:
            response = requests.post(
                self.embed_api_url,
                json={"texts": texts},
                timeout=300  # 5 
            )
            response.raise_for_status()
            return response.json()['embeddings']
        except requests.exceptions.RequestException as e:
            print(f"   : {e}")
            raise
    
    def is_low_quality_embedding(self, embedding: List[float]) -> Tuple[bool, str]:
        """
          
        
        Args:
            embedding:   (, numpy ,  )
            
        Returns:
            (is_low_quality, reason):   
        """
        #   (    )
        if isinstance(embedding, str):
            # PostgreSQL vector     
            # : "[0.1,0.2,0.3]"  "np.str_('[0.1,0.2,0.3]')"
            embedding_str = embedding.strip()
            
            # numpy string wrapper 
            if embedding_str.startswith('np.str_('):
                embedding_str = embedding_str[8:-1]  # "np.str_("  ")" 
            
            #  
            embedding_str = embedding_str.strip("'\"")
            
            #    
            embedding_str = embedding_str.strip('[]')
            values = [x.strip() for x in embedding_str.split(',') if x.strip()]
            
            try:
                embedding = [float(x) for x in values]
            except ValueError as e:
                return True, f"  : {str(e)[:50]}"
        
        try:
            vec = np.array(embedding, dtype=float)
        except Exception as e:
            return True, f"numpy   : {str(e)[:50]}"
        
        #  1: Norm   (  )
        norm = np.linalg.norm(vec)
        if norm < 0.1:
            return True, f"norm   ({norm:.4f})"
        
        #  2:    (  )
        variance = np.var(vec)
        if variance < 0.001:
            return True, f"   ({variance:.6f})"
        
        #  3: NaN Inf  
        if np.isnan(vec).any() or np.isinf(vec).any():
            return True, "NaN  Inf  "
        
        #  4:    (  0 )
        near_zero = np.abs(vec) < 0.001
        if near_zero.sum() / len(vec) > 0.9:
            return True, f"  ({near_zero.sum()}/{len(vec)}  ~0)"
        
        return False, ""
    
    def embed_chunks(self, chunks_to_embed: List[Tuple[str, str]]):
        """      """
        if not chunks_to_embed:
            return
        
        print(f"\n  : {len(chunks_to_embed)} ")
        
        #  
        with self.conn.cursor() as cur:
            for i in tqdm(range(0, len(chunks_to_embed), self.batch_size)):
                batch = chunks_to_embed[i:i + self.batch_size]
                chunk_ids = [c[0] for c in batch]
                texts = [c[1] for c in batch]
                
                try:
                    #  
                    embeddings = self.generate_embeddings(texts)
                    
                    # DB    
                    update_query = """
                        UPDATE chunks
                        SET embedding = %s::vector
                        WHERE chunk_id = %s
                    """
                    
                    for chunk_id, embedding, text in zip(chunk_ids, embeddings, texts):
                        #  
                        is_low_quality, reason = self.is_low_quality_embedding(embedding)
                        
                        if is_low_quality:
                            self.stats['low_quality_embeddings'] += 1
                            warning_msg = (
                                f"  : {chunk_id}\n"
                                f"  : {reason}\n"
                                f"   : {len(text)}\n"
                                f"   : {text[:100]}..."
                            )
                            self.stats['quality_warnings'].append(warning_msg)
                            
                            #    5 
                            if self.stats['low_quality_embeddings'] <= 5:
                                print(f"\n  {warning_msg}")
                        
                        #   (  )
                        cur.execute(update_query, (embedding, chunk_id))
                    
                    self.conn.commit()
                    self.stats['chunks_embedded'] += len(batch)
                    
                except Exception as e:
                    error_msg = f" {i//self.batch_size + 1}  : {e}"
                    print(f" {error_msg}")
                    self.stats['errors'].append(error_msg)
                    self.conn.rollback()
        
        print(f" {self.stats['chunks_embedded']}   ")
        
        #   
        if self.stats['low_quality_embeddings'] > 0:
            quality_rate = (self.stats['low_quality_embeddings'] / self.stats['chunks_embedded']) * 100
            print(f"   : {self.stats['low_quality_embeddings']} ({quality_rate:.1f}%)")
    
    def process_json_file(self, json_file: Path):
        """JSON  """
        print("\n" + "=" * 80)
        print(f" : {json_file.name}")
        print("=" * 80)
        
        # JSON 
        data = self.load_json_file(json_file)
        documents = data.get('documents', [])
        
        if not documents:
            print("   . .")
            return
        
        print(f"  : {len(documents)}")
        
        #  
        self.insert_documents(documents)
        
        #    
        all_chunks_to_embed = []
        
        for doc in tqdm(documents, desc=" "):
            chunks = doc.get('chunks', [])
            chunks_to_embed = self.insert_chunks(doc['doc_id'], chunks)
            all_chunks_to_embed.extend(chunks_to_embed)
        
        print(f"   : {self.stats['chunks']}")
        if self.stats['chunks_skipped'] > 0:
            print(f"⏭    (drop=True): {self.stats['chunks_skipped']}")
        if self.stats['chunks_empty'] > 0:
            print(f"   content : {self.stats['chunks_empty']}")
        
        #  
        if self.load_only:
            print(f"   : {len(all_chunks_to_embed):,}    .")
            print("       :")
            print("   conda run -n dsr python backend/scripts/embedding/embedding_tool.py --generate-local")
        elif all_chunks_to_embed:
            if not self.api_available:
                print("  API  .  .")
                print("       :")
                print("   conda run -n dsr python backend/scripts/embedding/embedding_tool.py --generate-local")
            else:
                self.embed_chunks(all_chunks_to_embed)
        else:
            print("    .")
    
    def process_all_files(self, data_dir: Path = None):
        """ JSON  """
        if data_dir is None:
            data_dir = DATA_DIR / "transformed"
        
        print("\n" + "=" * 80)
        print(f" : {data_dir}")
        print("=" * 80)
        
        # JSON   (transformation_summary.json )
        json_files = [
            f for f in data_dir.glob('*.json')
            if f.name != 'transformation_summary.json' and f.name != 'validation_result.json'
        ]
        
        if not json_files:
            print(f" {data_dir} JSON  .")
            return
        
        print(f"  : {len(json_files)}")
        for f in json_files:
            print(f"  - {f.name}")
        
        # DB 
        self.connect_db()
        
        #   
        for json_file in json_files:
            try:
                self.process_json_file(json_file)
            except Exception as e:
                error_msg = f"{json_file.name}  : {e}"
                print(f" {error_msg}")
                self.stats['errors'].append(error_msg)
                import traceback
                traceback.print_exc()
        
        #  
        self.print_stats()
        
        #  
        self.close_db()
    
    def print_stats(self):
        """  ()"""
        print("\n" + "=" * 80)
        print("   ")
        print("=" * 80)
        print(f":                 {self.stats['documents']:,}")
        print(f" ():          {self.stats['chunks']:,}")
        print(f" (/drop):     {self.stats['chunks_skipped']:,}")
        print(f" ( content):    {self.stats['chunks_empty']:,}")
        
        #   ()
        print(f"\n[]")
        print(f" :          {self.stats['chunks_preprocessed']:,}")
        print(f"  :   {self.stats['low_quality_texts']:,}")
        if self.stats['chunks_preprocessed'] > 0:
            filter_rate = (self.stats['low_quality_texts'] / self.stats['chunks_preprocessed']) * 100
            print(f"   :        {filter_rate:.1f}%")
        
        #  
        print(f"\n[]")
        print(f" :          {self.stats['chunks_embedded']:,}")
        
        #  
        if self.stats['chunks_embedded'] > 0:
            quality_rate = (self.stats['low_quality_embeddings'] / self.stats['chunks_embedded']) * 100
            print(f" :        {self.stats['low_quality_embeddings']:,} ({quality_rate:.1f}%)")
        
        if self.stats['quality_warnings']:
            print(f"\n   : {len(self.stats['quality_warnings'])}")
            #  3 
            for warning in self.stats['quality_warnings'][:3]:
                print(f"  {warning}")
            if len(self.stats['quality_warnings']) > 3:
                print(f"  ...  {len(self.stats['quality_warnings']) - 3}")
        
        if self.stats['errors']:
            print(f"\n : {len(self.stats['errors'])}")
            for error in self.stats['errors'][:10]:  #  10 
                print(f"  - {error}")
            if len(self.stats['errors']) > 10:
                print(f"  ...  {len(self.stats['errors']) - 10}")
    
    def verify_data(self):
        """    """
        print("\n" + "=" * 80)
        print("  ")
        print("=" * 80)
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            #  
            cur.execute("""
                SELECT doc_type, COUNT(*) as count
                FROM documents
                GROUP BY doc_type
                ORDER BY count DESC
            """)
            print("\n  :")
            for row in cur.fetchall():
                print(f"  {row['doc_type']}: {row['count']:,}")
            
            #  
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(embedding) as embedded,
                    COUNT(*) - COUNT(embedding) as not_embedded
                FROM chunks
                WHERE drop = FALSE
            """)
            chunk_stats = cur.fetchone()
            print(f"\n  :")
            print(f"  :           {chunk_stats['total']:,}")
            print(f"   :    {chunk_stats['embedded']:,}")
            print(f"   :  {chunk_stats['not_embedded']:,}")
            
            if chunk_stats['total'] > 0:
                embed_rate = (chunk_stats['embedded'] / chunk_stats['total']) * 100
                print(f"   :    {embed_rate:.1f}%")
            
            # chunk_type 
            cur.execute("""
                SELECT chunk_type, COUNT(*) as count
                FROM chunks
                WHERE drop = FALSE
                GROUP BY chunk_type
                ORDER BY count DESC
                LIMIT 10
            """)
            print(f"\n    ( 10):")
            for row in cur.fetchall():
                print(f"  {row['chunk_type']}: {row['count']:,}")
            
            # drop 
            cur.execute("SELECT COUNT(*) FROM chunks WHERE drop = TRUE")
            drop_result = cur.fetchone()
            dropped = drop_result['count'] if drop_result else 0
            if dropped > 0:
                print(f"\n⏭    (drop=True): {dropped:,}")
            
            #     (5)
            if chunk_stats['not_embedded'] > 0:
                cur.execute("""
                    SELECT chunk_id, doc_id, content_length, 
                           LEFT(content, 50) as content_preview
                    FROM chunks
                    WHERE embedding IS NULL AND drop = FALSE
                    LIMIT 5
                """)
                print(f"\n     :")
                for row in cur.fetchall():
                    print(f"  {row['chunk_id']}")
                    print(f"    : {row['content_length']}")
                    print(f"    : {row['content_preview']}...")
            
            #    ()
            if chunk_stats['embedded'] > 0:
                print(f"\n    ( 100):")
                cur.execute("""
                    SELECT embedding
                    FROM chunks
                    WHERE embedding IS NOT NULL AND drop = FALSE
                    ORDER BY RANDOM()
                    LIMIT 100
                """)
                
                low_quality_count = 0
                quality_issues = []
                
                for row in cur.fetchall():
                    embedding = row['embedding']
                    is_low_quality, reason = self.is_low_quality_embedding(embedding)
                    if is_low_quality:
                        low_quality_count += 1
                        quality_issues.append(reason)
                
                sample_size = min(100, chunk_stats['embedded'])
                print(f"   :          {sample_size}")
                print(f"   :      {low_quality_count}")
                
                if low_quality_count > 0:
                    quality_rate = (low_quality_count / sample_size) * 100
                    print(f"   :        {quality_rate:.1f}%")
                    
                    #  
                    from collections import Counter
                    issue_counter = Counter(quality_issues)
                    print(f"   :")
                    for issue, count in issue_counter.most_common(3):
                        print(f"    - {issue}: {count}")
                else:
                    print(f"   :           ")


def main():
    """ """
    import argparse
    
    parser = argparse.ArgumentParser(description='  ')
    parser.add_argument('--load-only', action='store_true', 
                       help='    ')
    args = parser.parse_args()
    
    #    
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    embed_api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
    
    print("=" * 80)
    if args.load_only:
        print("    ( )")
    else:
        print("   ")
    print("=" * 80)
    print(f": {db_config['host']}:{db_config['port']}/{db_config['database']}")
    print(f" API: {embed_api_url}")
    
    #  
    try:
        pipeline = EmbeddingPipeline(db_config, embed_api_url, load_only=args.load_only)
        pipeline.process_all_files()
        
        # 
        pipeline.connect_db()
        pipeline.verify_data()
        pipeline.close_db()
        
        print("\n" + "=" * 80)
        print("   !")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n  : {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
