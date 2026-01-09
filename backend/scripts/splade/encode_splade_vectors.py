"""
SPLADE Sparse Vector   
 chunk  SPLADE sparse vector  RDB 
"""

import os
import sys
import json
import psycopg2
from typing import List, Tuple, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
import numpy as np

#    
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

#   
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = backend_dir.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# SPLADE  import
try:
    from scripts.splade.test_splade_naver import NaverSPLADERetriever
    from scripts.splade.test_splade_remote import RemoteSPLADERetriever
    SPLADE_AVAILABLE = True
except ImportError as e:
    print(f"  SPLADE    : {e}")
    SPLADE_AVAILABLE = False


class SPLADEEncodingPipeline:
    """SPLADE sparse vector  """
    
    def __init__(
        self,
        db_config: Dict,
        batch_size: int = 32,
        use_remote: bool = False,
        api_url: str = None,
        device: str = None
    ):
        """
        Args:
            db_config:   
            batch_size:   (: 32)
            use_remote:  API   
            api_url:  API URL (use_remote=True )
            device:     ('cuda'  'cpu')
        """
        self.db_config = db_config
        self.batch_size = batch_size
        self.conn = None
        self.splade_retriever = None
        
        # SPLADE Retriever 
        if use_remote:
            if api_url is None:
                api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
            try:
                self.splade_retriever = RemoteSPLADERetriever(api_url=api_url)
                print(f"  SPLADE API  : {api_url}")
            except Exception as e:
                print(f"   API   : {e}")
                print("      ...")
                use_remote = False
        
        if not use_remote:
            try:
                self.splade_retriever = NaverSPLADERetriever(device=device)
                self.splade_retriever.load_model()
                print(f"  SPLADE  : device={self.splade_retriever.device}")
            except Exception as e:
                print(f" SPLADE   : {e}")
                raise RuntimeError("SPLADE    .")
    
    def connect_db(self):
        """ """
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
            self.conn.autocommit = False
    
    def get_chunks_to_encode(
        self,
        doc_type: Optional[str] = None,
        limit: Optional[int] = None,
        skip_encoded: bool = True
    ) -> List[Tuple[str, str]]:
        """
          chunk  
        
        Args:
            doc_type:    (None )
            limit:   (None )
            skip_encoded:   chunk 
        
        Returns:
            (chunk_id, content)  
        """
        self.connect_db()
        cur = self.conn.cursor()
        
        where_clauses = []
        params = []
        
        if skip_encoded:
            where_clauses.append("(splade_encoded IS NULL OR splade_encoded = FALSE)")
        
        if doc_type:
            where_clauses.append("d.doc_type = %s")
            params.append(doc_type)
        
        where_clauses.append("c.drop = FALSE")
        where_clauses.append("c.content IS NOT NULL")
        where_clauses.append("LENGTH(TRIM(c.content)) > 0")
        
        where_sql = " AND ".join(where_clauses)
        
        limit_sql = ""
        if limit:
            limit_sql = f"LIMIT {limit}"
        
        sql = f"""
            SELECT c.chunk_id, c.content
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE {where_sql}
            ORDER BY c.chunk_id
            {limit_sql}
        """
        
        cur.execute(sql, params)
        results = cur.fetchall()
        cur.close()
        
        return results
    
    def sparse_vector_to_jsonb(self, sparse_vec: np.ndarray, threshold: float = 0.0) -> Dict[str, float]:
        """
        Sparse vector JSONB  
        0     
        
        Args:
            sparse_vec: Sparse vector (numpy array)
            threshold:    
        
        Returns:
            {token_id: weight}  
        """
        # 0   
        non_zero_indices = np.where(sparse_vec > threshold)[0]
        
        # JSONB   (  )
        result = {}
        for idx in non_zero_indices:
            weight = float(sparse_vec[idx])
            if weight > threshold:
                result[str(idx)] = weight
        
        return result
    
    def encode_batch(self, chunks: List[Tuple[str, str]]) -> List[Dict]:
        """
         chunk 
        
        Args:
            chunks: (chunk_id, content)  
        
        Returns:
               [{chunk_id, sparse_vector, success}, ...]
        """
        if not chunks:
            return []
        
        chunk_ids = [c[0] for c in chunks]
        contents = [c[1] for c in chunks]
        
        results = []
        
        try:
            #  
            if hasattr(self.splade_retriever, 'encode_documents_batch'):
                # RemoteSPLADERetriever   
                sparse_vectors = self.splade_retriever.encode_documents_batch(contents)
            else:
                # NaverSPLADERetriever   
                sparse_vectors = []
                for content in contents:
                    try:
                        vec = self.splade_retriever.encode_document(content)
                        sparse_vectors.append(vec)
                    except Exception as e:
                        print(f"      (chunk_id ): {e}")
                        sparse_vectors.append(None)
            
            #  
            for chunk_id, sparse_vec in zip(chunk_ids, sparse_vectors):
                if sparse_vec is None:
                    results.append({
                        'chunk_id': chunk_id,
                        'sparse_vector': None,
                        'success': False
                    })
                    continue
                
                # JSONB  
                sparse_jsonb = self.sparse_vector_to_jsonb(sparse_vec)
                
                results.append({
                    'chunk_id': chunk_id,
                    'sparse_vector': sparse_jsonb,
                    'success': True
                })
        
        except Exception as e:
            print(f"      : {e}")
            #   
            for chunk_id, content in chunks:
                try:
                    sparse_vec = self.splade_retriever.encode_document(content)
                    sparse_jsonb = self.sparse_vector_to_jsonb(sparse_vec)
                    results.append({
                        'chunk_id': chunk_id,
                        'sparse_vector': sparse_jsonb,
                        'success': True
                    })
                except Exception as e2:
                    print(f"       (chunk_id: {chunk_id[:50]}...): {e2}")
                    results.append({
                        'chunk_id': chunk_id,
                        'sparse_vector': None,
                        'success': False
                    })
        
        return results
    
    def save_encoded_vectors(self, encoded_results: List[Dict]):
        """
         sparse vector DB 
        
        Args:
            encoded_results: encode_batch() 
        """
        if not encoded_results:
            return
        
        self.connect_db()
        cur = self.conn.cursor()
        
        model_name = 'naver/splade-v3'
        if hasattr(self.splade_retriever, 'model_name'):
            model_name = self.splade_retriever.model_name
        
        success_count = 0
        fail_count = 0
        
        for result in encoded_results:
            chunk_id = result['chunk_id']
            sparse_vector = result['sparse_vector']
            success = result['success']
            
            if success and sparse_vector:
                try:
                    # JSONB  
                    sparse_jsonb = json.dumps(sparse_vector)
                    
                    cur.execute("""
                        UPDATE chunks
                        SET 
                            splade_sparse_vector = %s::jsonb,
                            splade_model = %s,
                            splade_encoded = TRUE,
                            updated_at = NOW()
                        WHERE chunk_id = %s
                    """, (sparse_jsonb, model_name, chunk_id))
                    
                    success_count += 1
                except Exception as e:
                    print(f"    DB   (chunk_id: {chunk_id[:50]}...): {e}")
                    fail_count += 1
            else:
                #     (  )
                try:
                    cur.execute("""
                        UPDATE chunks
                        SET splade_encoded = FALSE
                        WHERE chunk_id = %s
                    """, (chunk_id,))
                    fail_count += 1
                except Exception as e:
                    print(f"       (chunk_id: {chunk_id[:50]}...): {e}")
        
        self.conn.commit()
        cur.close()
        
        return success_count, fail_count
    
    def encode_all_chunks(
        self,
        doc_type: Optional[str] = None,
        limit: Optional[int] = None,
        resume: bool = True
    ):
        """
         chunk  SPLADE  
        
        Args:
            doc_type:   
            limit:   
            resume:   chunk 
        """
        print("\n" + "=" * 80)
        print("SPLADE Sparse Vector  ")
        print("=" * 80)
        
        #   chunk 
        chunks = self.get_chunks_to_encode(
            doc_type=doc_type,
            limit=limit,
            skip_encoded=resume
        )
        
        total_chunks = len(chunks)
        if total_chunks == 0:
            print("  chunk .")
            return
        
        print(f"\n  : {total_chunks} chunk")
        if doc_type:
            print(f"    : {doc_type}")
        
        #  
        total_success = 0
        total_fail = 0
        
        with tqdm(total=total_chunks, desc=" ") as pbar:
            for i in range(0, total_chunks, self.batch_size):
                batch = chunks[i:i + self.batch_size]
                
                #  
                encoded_results = self.encode_batch(batch)
                
                # DB 
                success_count, fail_count = self.save_encoded_vectors(encoded_results)
                
                total_success += success_count
                total_fail += fail_count
                
                pbar.update(len(batch))
                pbar.set_postfix({
                    '': total_success,
                    '': total_fail,
                    '': f"{total_success + total_fail}/{total_chunks}"
                })
        
        #  
        print("\n" + "=" * 80)
        print(" ")
        print("=" * 80)
        print(f" : {total_success}")
        print(f" : {total_fail}")
        print(f"  : {total_success + total_fail} / {total_chunks}")
        
        if total_fail > 0:
            print(f"\n   chunk    .")
    
    def get_statistics(self) -> Dict:
        """   """
        self.connect_db()
        cur = self.conn.cursor()
        
        #  
        cur.execute("""
            SELECT 
                COUNT(*) as total_chunks,
                COUNT(CASE WHEN splade_encoded = TRUE THEN 1 END) as encoded_chunks,
                COUNT(CASE WHEN splade_encoded = FALSE OR splade_encoded IS NULL THEN 1 END) as unencoded_chunks
            FROM chunks
            WHERE drop = FALSE
        """)
        total_stats = cur.fetchone()
        
        #   
        cur.execute("""
            SELECT 
                d.doc_type,
                COUNT(*) as total,
                COUNT(CASE WHEN c.splade_encoded = TRUE THEN 1 END) as encoded
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.drop = FALSE
            GROUP BY d.doc_type
            ORDER BY total DESC
        """)
        doc_type_stats = cur.fetchall()
        
        cur.close()
        
        return {
            'total': {
                'total_chunks': total_stats[0],
                'encoded_chunks': total_stats[1],
                'unencoded_chunks': total_stats[2],
                'encode_rate': (total_stats[1] / total_stats[0] * 100) if total_stats[0] > 0 else 0
            },
            'by_doc_type': [
                {
                    'doc_type': row[0],
                    'total': row[1],
                    'encoded': row[2],
                    'rate': (row[2] / row[1] * 100) if row[1] > 0 else 0
                }
                for row in doc_type_stats
            ]
        }


def main():
    """ """
    import argparse
    
    parser = argparse.ArgumentParser(description='SPLADE Sparse Vector  ')
    parser.add_argument('--doc-type', type=str, help='   (: law, criteria_*)')
    parser.add_argument('--limit', type=int, help='  ')
    parser.add_argument('--batch-size', type=int, default=32, help='  (: 32)')
    parser.add_argument('--remote', action='store_true', help=' API  ')
    parser.add_argument('--api-url', type=str, help=' API URL')
    parser.add_argument('--device', type=str, choices=['cuda', 'cpu'], help='  ')
    parser.add_argument('--no-resume', action='store_true', help='  chunk ')
    parser.add_argument('--stats-only', action='store_true', help='  ')
    
    args = parser.parse_args()
    
    # DB 
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    #  
    try:
        pipeline = SPLADEEncodingPipeline(
            db_config=db_config,
            batch_size=args.batch_size,
            use_remote=args.remote,
            api_url=args.api_url,
            device=args.device
        )
    except Exception as e:
        print(f"   : {e}")
        sys.exit(1)
    
    #  
    if args.stats_only:
        stats = pipeline.get_statistics()
        print("\n SPLADE  ")
        print("=" * 80)
        print(f" chunk: {stats['total']['total_chunks']}")
        print(f" : {stats['total']['encoded_chunks']}")
        print(f" : {stats['total']['unencoded_chunks']}")
        print(f" : {stats['total']['encode_rate']:.1f}%")
        print("\n :")
        for dt in stats['by_doc_type']:
            print(f"  {dt['doc_type']}: {dt['encoded']}/{dt['total']} ({dt['rate']:.1f}%)")
        return
    
    #  
    pipeline.encode_all_chunks(
        doc_type=args.doc_type,
        limit=args.limit,
        resume=not args.no_resume
    )
    
    #   
    stats = pipeline.get_statistics()
    print("\n  ")
    print("=" * 80)
    print(f" : {stats['total']['encode_rate']:.1f}%")
    
    #  
    if pipeline.conn:
        pipeline.conn.close()


if __name__ == "__main__":
    main()
