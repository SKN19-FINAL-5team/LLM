#!/usr/bin/env python3
"""
  
  , /    

:
    python backend/scripts/embedding/embedding_tool.py --check
    python backend/scripts/embedding/embedding_tool.py --generate-local
    python backend/scripts/embedding/embedding_tool.py --generate-remote
    python backend/scripts/embedding/embedding_tool.py --generate-remote --api-url http://localhost:8001/embed
"""

import os
import sys
import json
import psycopg2
import argparse
import requests
import torch
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer
from psycopg2.extras import RealDictCursor

#   
backend_dir = Path(__file__).parent.parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = backend_dir.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# DB  
DB_CONFIG = {
    'host': os.getenv('DB_HOST', os.getenv('POSTGRES_HOST', 'localhost')),
    'port': int(os.getenv('DB_PORT', os.getenv('POSTGRES_PORT', 5432))),
    'database': os.getenv('DB_NAME', os.getenv('POSTGRES_DB', 'ddoksori')),
    'user': os.getenv('DB_USER', os.getenv('POSTGRES_USER', 'postgres')),
    'password': os.getenv('DB_PASSWORD', os.getenv('POSTGRES_PASSWORD', 'postgres'))
}


class EmbeddingTool:
    """  """
    
    def __init__(self):
        self.conn = None
        self._connect()
    
    def _connect(self):
        """ """
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            print(f"   : {e}")
            raise
    
    def check_status(self):
        """   ( check_embedding_status.py )"""
        cur = self.conn.cursor()
        
        print("=" * 70)
        print("  -     ")
        print("=" * 70)
        
        # 1.  
        print("\n  ")
        print("-" * 70)
        
        cur.execute("SELECT COUNT(*) FROM documents")
        doc_count = cur.fetchone()[0]
        print(f"  : {doc_count:,}")
        
        cur.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cur.fetchone()[0]
        print(f"  : {chunk_count:,}")
        
        cur.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL")
        embedded_count = cur.fetchone()[0]
        embedding_rate = (embedded_count / chunk_count * 100) if chunk_count > 0 else 0
        print(f"  : {embedded_count:,}")
        print(f" : {embedding_rate:.2f}%")
        
        if embedding_rate < 100:
            print(f"   {chunk_count - embedded_count:,}    .")
        else:
            print("    !")
        
        # 2.   
        print("\n   ")
        print("-" * 70)
        cur.execute("""
            SELECT 
                doc_type,
                COUNT(*) as count
            FROM documents
            GROUP BY doc_type
            ORDER BY doc_type
        """)
        print(f"{' ':<30} {' ':>15}")
        print("-" * 70)
        for row in cur.fetchall():
            print(f"{row[0]:<30} {row[1]:>15,}")
        
        # 3.   
        print("\n    ( 10)")
        print("-" * 70)
        cur.execute("""
            SELECT 
                chunk_type,
                COUNT(*) as count,
                AVG(content_length) as avg_length
            FROM chunks
            GROUP BY chunk_type
            ORDER BY count DESC
            LIMIT 10
        """)
        print(f"{' ':<30} {' ':>15} {' ':>15}")
        print("-" * 70)
        for row in cur.fetchall():
            chunk_type = row[0] if row[0] else '(null)'
            print(f"{chunk_type:<30} {row[1]:>15,} {row[2]:>14.0f}")
        
        # 4.   
        print("\n   ")
        print("-" * 70)
        cur.execute("""
            SELECT 
                MIN(content_length) as min_length,
                AVG(content_length) as avg_length,
                MAX(content_length) as max_length,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY content_length) as median_length
            FROM chunks
        """)
        row = cur.fetchone()
        if row and row[0] is not None:
            print(f" : {row[0]:,}")
            print(f" : {row[1]:.0f}")
            print(f": {row[2]:.0f}")
            print(f" : {row[3]:,}")
        else:
            print(" .")
        
        # 5.  
        print("\n  ")
        print("-" * 70)
        cur.execute("""
            SELECT 
                source_org,
                COUNT(DISTINCT d.doc_id) as document_count,
                COUNT(c.chunk_id) as chunk_count
            FROM documents d
            LEFT JOIN chunks c ON d.doc_id = c.doc_id
            GROUP BY source_org
            ORDER BY document_count DESC
        """)
        print(f"{'':<30} {' ':>15} {' ':>15}")
        print("-" * 70)
        for row in cur.fetchall():
            source = row[0] if row[0] else '(null)'
            print(f"{source:<30} {row[1]:>15,} {row[2]:>15,}")
        
        # 6.   
        print("\n   ")
        print("-" * 70)
        cur.execute("""
            SELECT DISTINCT 
                embedding_model,
                array_length(embedding::real[], 1) as dimension
            FROM chunks
            WHERE embedding IS NOT NULL
            LIMIT 5
        """)
        rows = cur.fetchall()
        if rows:
            for row in rows:
                print(f": {row[0]}, : {row[1]}")
        else:
            print("  .")
        
        # 7.   
        print("\n   (5)")
        print("-" * 70)
        cur.execute("""
            SELECT 
                c.chunk_id,
                d.doc_type,
                c.chunk_type,
                c.content_length,
                LEFT(c.content, 100) as content_preview,
                CASE WHEN c.embedding IS NOT NULL THEN 'YES' ELSE 'NO' END as has_embedding
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            ORDER BY RANDOM()
            LIMIT 5
        """)
        for i, row in enumerate(cur.fetchall(), 1):
            print(f"\n[{i}] {row[0]}")
            print(f"     : {row[1]}")
            print(f"     : {row[2]}")
            print(f"    : {row[3]:,}")
            print(f"    : {row[5]}")
            print(f"    : {row[4]}...")
        
        # 8.   
        print("\n    ")
        print("-" * 70)
        
        #   
        cur.execute("SELECT COUNT(*) FROM chunks WHERE content_length < 10")
        short_chunks = cur.fetchone()[0]
        if short_chunks > 0:
            print(f"  10  : {short_chunks:,}")
        else:
            print(" 10   ")
        
        #   
        cur.execute("SELECT COUNT(*) FROM chunks WHERE content_length > 5000")
        long_chunks = cur.fetchone()[0]
        if long_chunks > 0:
            print(f"  5000  : {long_chunks:,}")
        else:
            print(" 5000   ")
        
        #   
        cur.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NULL")
        missing_embeddings = cur.fetchone()[0]
        if missing_embeddings > 0:
            print(f"    : {missing_embeddings:,}")
        else:
            print("    ")
        
        print("\n" + "=" * 70)
        print(" !")
        print("=" * 70)
        
        cur.close()
    
    def generate_local(self, batch_size=8, device='auto'):
        """    ( generate_embeddings_incremental.py )"""
        start_time = datetime.now()
        
        print("=" * 80)
        print("   (,  )")
        print("=" * 80)
        print(f" : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        cur = self.conn.cursor()
        
        #    
        print("\n    ...")
        cur.execute("""
            SELECT chunk_id, content, doc_id
            FROM chunks
            WHERE drop = FALSE AND embedding IS NULL
            ORDER BY doc_id, chunk_index
        """)
        
        chunks = cur.fetchall()
        print(f" {len(chunks):,}  ")
        
        if len(chunks) == 0:
            print("\n    !")
            cur.close()
            return
        
        #   
        cur.execute("""
            SELECT d.doc_type, COUNT(*) as count
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.drop = FALSE AND c.embedding IS NULL
            GROUP BY d.doc_type
            ORDER BY count DESC
        """)
        print("\n   :")
        for doc_type, count in cur.fetchall():
            print(f"  - {doc_type}: {count:,}")
        
        #  
        print("\n  ...")
        if device == 'auto':
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            device = torch.device(device)
        
        print(f"  : {device}")
        
        if device.type == 'cuda':
            print(f"  GPU : {torch.cuda.get_device_name(0)}")
            print(f"  GPU : {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        
        model_name = 'nlpai-lab/KURE-v1'
        print(f"  : {model_name}")
        
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModel.from_pretrained(model_name).to(device)
            model.eval()
            print("   ")
        except Exception as e:
            print(f"   : {e}")
            cur.close()
            return
        
        #    
        if device.type == 'cuda':
            gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
            if gpu_memory_gb >= 16:
                batch_size = max(batch_size, 32)
            elif gpu_memory_gb >= 8:
                batch_size = max(batch_size, 16)
            else:
                batch_size = max(batch_size, 8)
        else:
            batch_size = max(batch_size, 4)
        
        print(f"   : {batch_size}")
        
        #  
        print(f"\n  ... ( {len(chunks):,})")
        chunk_ids = [c[0] for c in chunks]
        contents = [c[1] for c in chunks]
        
        embeddings = self._generate_embeddings_local(contents, model, tokenizer, device, batch_size)
        
        print(f"\n   : {len(embeddings):,}")
        
        # DB 
        print("\nDB  ...")
        updated = 0
        commit_interval = 100
        
        for idx, (chunk_id, embedding) in enumerate(zip(chunk_ids, embeddings), 1):
            try:
                cur.execute("""
                    UPDATE chunks
                    SET embedding = %s, updated_at = NOW()
                    WHERE chunk_id = %s
                """, (embedding.tolist(), chunk_id))
                
                updated += 1
                
                #  
                if idx % commit_interval == 0:
                    self.conn.commit()
                    progress = (idx / len(chunk_ids)) * 100
                    print(f"  : {idx:,}/{len(chunk_ids):,} ({progress:.1f}%) -  ")
            
            except Exception as e:
                print(f"\n   {chunk_id}  : {e}")
        
        #  
        self.conn.commit()
        print(f" DB  : {updated:,} ")
        
        # 
        end_time = datetime.now()
        duration = end_time - start_time
        
        cur.execute("""
            SELECT COUNT(*) 
            FROM chunks 
            WHERE drop = FALSE AND embedding IS NULL
        """)
        remaining = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(*) 
            FROM chunks 
            WHERE drop = FALSE
        """)
        total = cur.fetchone()[0]
        
        print("\n" + "=" * 80)
        print("  ")
        print("=" * 80)
        print(f"  -  : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  -  : {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  -  : {duration}")
        print(f"  -  : {len(embeddings):,}")
        print(f"  -  : {updated:,}")
        print(f"  -  : {remaining:,}")
        print(f"  -  : {total:,}")
        print(f"  -  : {((total - remaining) / total * 100):.1f}%")
        
        if remaining == 0:
            print("\n    !")
        else:
            print(f"\n  {remaining:,}    .")
        
        cur.close()
    
    def _generate_embeddings_local(self, texts, model, tokenizer, device, batch_size=8):
        """   """
        embeddings = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc=" ", unit="batch"):
            batch = texts[i:i+batch_size]
            
            try:
                inputs = tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors='pt'
                ).to(device)
                
                with torch.no_grad():
                    outputs = model(**inputs)
                    batch_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                
                embeddings.extend(batch_embeddings)
            
            except Exception as e:
                print(f"\n   {i//batch_size + 1}   : {e}")
                #   fallback
                for text in batch:
                    try:
                        inputs = tokenizer(
                            [text],
                            padding=True,
                            truncation=True,
                            max_length=512,
                            return_tensors='pt'
                        ).to(device)
                        
                        with torch.no_grad():
                            outputs = model(**inputs)
                            embedding = outputs.last_hidden_state[0, 0, :].cpu().numpy()
                        
                        embeddings.append(embedding)
                    except Exception as e2:
                        print(f"    : {e2}")
                        embeddings.append(torch.zeros(1024).numpy())
        
        return embeddings
    
    def generate_remote(self, api_url=None, batch_size=32):
        """ API   ( embed_existing_chunks.py )"""
        if api_url is None:
            api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
        
        print("=" * 80)
        print("    ( API )")
        print("=" * 80)
        print(f"API URL: {api_url}")
        
        # API  
        print(f"\n  API  : {api_url}")
        try:
            base_url = api_url.rsplit('/', 1)[0]
            response = requests.get(base_url, timeout=10)
            response.raise_for_status()
            print(f" API  ")
        except requests.exceptions.RequestException as e:
            print(f" API  : {e}")
            print("\n  :")
            print("1. RunPod   :")
            print("   ssh root@[IP] -p [PORT]")
            print("   uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000")
            print("\n2.  SSH  :")
            print("   ssh -L 8001:localhost:8000 root@[IP] -p [PORT] -N &")
            return
        
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        
        #    
        print("\n     ...")
        cur.execute("""
            SELECT chunk_id, content, doc_id
            FROM chunks
            WHERE drop = FALSE 
              AND embedding IS NULL
              AND content IS NOT NULL
              AND LENGTH(TRIM(content)) > 0
            ORDER BY doc_id, chunk_index
        """)
        
        chunks = cur.fetchall()
        print(f" {len(chunks):,}  ")
        
        if not chunks:
            print("\n    !")
            self._verify_result(cur)
            cur.close()
            return
        
        #   
        cur.execute("""
            SELECT d.doc_type, COUNT(*) as count
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.drop = FALSE 
              AND c.embedding IS NULL
              AND c.content IS NOT NULL
            GROUP BY d.doc_type
            ORDER BY count DESC
        """)
        
        print("\n :")
        for row in cur.fetchall():
            print(f"  - {row['doc_type']}: {row['count']:,}")
        
        #  
        print(f"\n   : {len(chunks):,} ")
        print(f"   : {batch_size}")
        
        start_time = datetime.now()
        stats = {
            'chunks_embedded': 0,
            'errors': []
        }
        
        cur2 = self.conn.cursor()
        
        for i in tqdm(range(0, len(chunks), batch_size), desc=" "):
            batch = chunks[i:i + batch_size]
            chunk_ids = [c['chunk_id'] for c in batch]
            texts = [c['content'] for c in batch]
            
            try:
                #  
                response = requests.post(
                    api_url,
                    json={"texts": texts},
                    timeout=300
                )
                response.raise_for_status()
                embeddings = response.json()['embeddings']
                
                # DB 
                update_query = """
                    UPDATE chunks
                    SET embedding = %s::vector,
                        updated_at = NOW()
                    WHERE chunk_id = %s
                """
                
                for chunk_id, embedding in zip(chunk_ids, embeddings):
                    cur2.execute(update_query, (embedding, chunk_id))
                
                self.conn.commit()
                stats['chunks_embedded'] += len(batch)
            
            except Exception as e:
                error_msg = f" {i//batch_size + 1} : {e}"
                print(f"\n {error_msg}")
                stats['errors'].append(error_msg)
                self.conn.rollback()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n   !")
        print(f"  -  : {stats['chunks_embedded']:,}")
        print(f"  -  : {duration}")
        if duration.total_seconds() > 0:
            print(f"  -  : {stats['chunks_embedded'] / duration.total_seconds():.1f} /")
        
        #  
        self._verify_result(cur)
        
        #  
        if stats['errors']:
            print(f"\n   : {len(stats['errors'])}")
            for error in stats['errors'][:5]:
                print(f"  - {error}")
            if len(stats['errors']) > 5:
                print(f"  ...  {len(stats['errors']) - 5}")
        
        cur.close()
        cur2.close()
    
    def _verify_result(self, cur):
        """ """
        print("\n" + "=" * 80)
        print("  ")
        print("=" * 80)
        
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(embedding) as embedded,
                COUNT(*) - COUNT(embedding) as not_embedded
            FROM chunks
            WHERE drop = FALSE
        """)
        stats = cur.fetchone()
        
        print(f"\n  :")
        print(f"  :         {stats['total']:,}")
        print(f"   :  {stats['embedded']:,}")
        print(f"   :  {stats['not_embedded']:,}")
        
        if stats['total'] > 0:
            coverage = (stats['embedded'] / stats['total']) * 100
            print(f"  :     {coverage:.1f}%")
            
            if stats['not_embedded'] == 0:
                print("\n    !")
            else:
                print(f"\n  {stats['not_embedded']:,}    .")
        
        #   
        cur.execute("""
            SELECT 
                d.doc_type,
                COUNT(*) as total,
                COUNT(c.embedding) as embedded
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.drop = FALSE
            GROUP BY d.doc_type
            ORDER BY total DESC
        """)
        
        print(f"\n  :")
        for row in cur.fetchall():
            coverage = (row['embedded'] / row['total']) * 100 if row['total'] > 0 else 0
            status = "" if coverage == 100 else ""
            print(f"  {status} {row['doc_type']:<30} {row['embedded']:>6}/{row['total']:<6} ({coverage:>5.1f}%)")
    
    def close(self):
        """ """
        if self.conn:
            self.conn.close()


def main():
    """  """
    parser = argparse.ArgumentParser(
        description='  ',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 :
  python embedding_tool.py --check                    #   
  python embedding_tool.py --generate-local            #   
  python embedding_tool.py --generate-local --batch-size 16  #   
  python embedding_tool.py --generate-remote           #  API  
  python embedding_tool.py --generate-remote --api-url http://localhost:8001/embed
        """
    )
    
    parser.add_argument('--check', action='store_true',
                       help='  ')
    parser.add_argument('--generate-local', action='store_true',
                       help='   ')
    parser.add_argument('--generate-remote', action='store_true',
                       help=' API  ')
    parser.add_argument('--batch-size', type=int, default=8,
                       help='  (: 8)')
    parser.add_argument('--device', type=str, default='auto',
                       help=' (cuda/cpu/auto, : auto)')
    parser.add_argument('--api-url', type=str, default=None,
                       help=' API URL (: EMBED_API_URL    http://localhost:8001/embed)')
    
    args = parser.parse_args()
    
    #     
    if not any([args.check, args.generate_local, args.generate_remote]):
        parser.print_help()
        return
    
    tool = EmbeddingTool()
    
    try:
        if args.check:
            tool.check_status()
        if args.generate_local:
            tool.generate_local(batch_size=args.batch_size, device=args.device)
        if args.generate_remote:
            tool.generate_remote(api_url=args.api_url, batch_size=args.batch_size)
    
    except KeyboardInterrupt:
        print("\n\n    .")
    except Exception as e:
        print(f"\n  : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        tool.close()


if __name__ == "__main__":
    main()
