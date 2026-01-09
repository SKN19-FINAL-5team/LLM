#!/usr/bin/env python3
"""
   

 (doc_type='law')   
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm

#    
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "scripts" / "embedding"))

from embed_data_remote import EmbeddingPipeline, DATA_DIR

load_dotenv()


class LawEmbeddingPipeline(EmbeddingPipeline):
    """    """
    
    def process_all_files(self, data_dir: Path = None):
        """   """
        if data_dir is None:
            data_dir = DATA_DIR / "law"
        
        print("\n" + "=" * 80)
        print("    ")
        print("=" * 80)
        print(f" : {data_dir}")
        print(f": doc_type = 'law'")
        
        # JSONL  
        jsonl_files = list(data_dir.glob('*.jsonl'))
        
        if not jsonl_files:
            print(f" {data_dir} JSONL  .")
            return
        
        print(f"  : {len(jsonl_files)}")
        for f in jsonl_files:
            print(f"  - {f.name}")
        
        # DB 
        self.connect_db()
        
        #   
        for jsonl_file in jsonl_files:
            try:
                self.process_jsonl_file(jsonl_file)
            except Exception as e:
                error_msg = f"{jsonl_file.name}  : {e}"
                print(f" {error_msg}")
                self.stats['errors'].append(error_msg)
                import traceback
                traceback.print_exc()
        
        #  
        self.print_stats()
        
        #  
        self.close_db()
    
    def process_jsonl_file(self, jsonl_file: Path):
        """JSONL   (  )"""
        print("\n" + "=" * 80)
        print(f" : {jsonl_file.name}")
        print("=" * 80)
        
        # JSONL 
        documents = []
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                    # doc_type 'law'  
                    if doc.get('doc_type') == 'law':
                        documents.append(doc)
                except json.JSONDecodeError as e:
                    print(f"  JSON  : {e}")
                    continue
        
        if not documents:
            print("    . .")
            return
        
        print(f"   : {len(documents)}")
        
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


def main():
    """ """
    import argparse
    
    parser = argparse.ArgumentParser(description='   ')
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
        print("     ( )")
    else:
        print("     ")
    print("=" * 80)
    print(f": {db_config['host']}:{db_config['port']}/{db_config['database']}")
    print(f" API: {embed_api_url}")
    
    #  
    try:
        pipeline = LawEmbeddingPipeline(db_config, embed_api_url, load_only=args.load_only)
        pipeline.process_all_files()
        
        # 
        pipeline.connect_db()
        pipeline.verify_data()
        pipeline.close_db()
        
        print("\n" + "=" * 80)
        print("    !")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n  : {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
