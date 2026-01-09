#!/usr/bin/env python3
"""
  

 JSONL  PostgreSQL   :
1. JSON   ()
2. PostgreSQL 

Features:
-  chunk_index 0-based 
-   
-    (   )
-  
"""

import json
import os
import glob
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

#   sys.path  metadata_enricher import 
import sys
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from metadata_enricher import MetadataEnricher

load_dotenv()

#      
SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/data_processing/
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # ddoksori_demo/
DATA_DIR = PROJECT_ROOT / "backend" / "data"

#     ( -    )
#  : KURE-v1  512  =  768-1024
#  :   400-800 
CHUNK_PROCESSING_RULES = {
    'decision': {
        'min_length': 100,
        'max_length': 600,  # :    (700 → 600)
        'target_length': 500,  # :    (600 → 500)
        'merge_allowed': False,  #   
        'split_allowed': True,
        'overlap_size': 100,
        'overlap_mode': 'sentence',  # :   
        'drop_if_empty': True,
        'description': '() -  '
    },
    'reasoning': {
        'min_length': 150,
        'max_length': 800,  # :     (700 → 800)
        'target_length': 700,  # :    (600 → 700)
        'merge_allowed': True,
        'split_allowed': True,
        'overlap_size': 150,
        'overlap_mode': 'sentence',
        'description': '() -   '
    },
    'judgment': {
        'min_length': 150,
        'max_length': 800,  # :     (700 → 800)
        'target_length': 700,  # :    (600 → 700)
        'merge_allowed': True,
        'split_allowed': True,
        'overlap_size': 150,
        'overlap_mode': 'sentence',
        'description': ' -   '
    },
    'parties_claim': {
        'min_length': 150,
        'max_length': 750,  # :    
        'target_length': 650,
        'merge_allowed': True,
        'split_allowed': True,
        'overlap_size': 150,
        'overlap_mode': 'sentence',
        'description': '  - '
    },
    'law': {
        'min_length': 50,
        'max_length': 500,  # :     (700 → 500)
        'target_length': 400,  # :    (600 → 400)
        'merge_allowed': False,
        'split_allowed': True,
        'overlap_size': 80,  # :    (100 → 80)
        'overlap_mode': 'sentence',
        'drop_if_empty': True,
        'enrich_with_metadata': True,
        'description': ' '
    },
    'law_reference': {
        'min_length': 50,
        'max_length': 500,  # :    (700 → 500)
        'target_length': 400,
        'merge_allowed': False,
        'split_allowed': True,
        'overlap_size': 80,
        'overlap_mode': 'sentence',
        'drop_if_empty': True,
        'description': ' '
    },
    'resolution_row': {
        'min_length': 100,
        'max_length': 700,
        'target_length': 600,
        'merge_allowed': False,
        'split_allowed': True,
        'overlap_size': 100,
        'overlap_mode': 'sentence',
        'description': ' '
    },
    'qa_combined': {
        'min_length': 150,
        'max_length': 700,
        'target_length': 600,
        'merge_allowed': False,  # Q&A   
        'split_allowed': True,
        'overlap_size': 100,
        'overlap_mode': 'sentence',
        'description': ' '
    },
    'article': {
        'min_length': 100,
        'max_length': 500,  # :   (700 → 500)
        'target_length': 400,
        'merge_allowed': False,
        'split_allowed': True,
        'overlap_size': 80,
        'overlap_mode': 'sentence',
        'description': ''
    },
    'paragraph': {
        'min_length': 100,
        'max_length': 600,  # :   (700 → 600)
        'target_length': 500,
        'merge_allowed': True,
        'split_allowed': True,
        'overlap_size': 100,
        'overlap_mode': 'sentence',
        'description': ''
    },
    #  
    'default': {
        'min_length': 100,
        'max_length': 700,
        'target_length': 600,
        'merge_allowed': True,
        'split_allowed': True,
        'overlap_size': 100,
        'overlap_mode': 'sentence',
        'drop_if_empty': True,
        'description': ' '
    }
}

class DataTransformer:
    """  """
    
    def __init__(self, output_dir: Path = None, use_db: bool = False, enrich_metadata: bool = True):
        """
        Args:
            output_dir:     (None  )
            use_db: DB  
            enrich_metadata:   
        """
        if output_dir is None:
            output_dir = DATA_DIR / "transformed"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.use_db = use_db
        self.conn = None
        self.cur = None
        
        if use_db:
            self._connect_db()
        
        self.enrich_metadata = enrich_metadata
        if enrich_metadata:
            self.metadata_enricher = MetadataEnricher()
            print("   ")
        else:
            self.metadata_enricher = None
        
        self.stats = {
            'documents': 0,
            'chunks': 0,
            'skipped': 0,
            'errors': [],
            'enriched_chunks': 0
        }
    
    def _connect_db(self):
        """ """
        self.conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        self.cur = self.conn.cursor()
        print("   ")
    
    def _assign_chunk_indices(self, chunks: List[Dict]) -> List[Dict]:
        """
          0-based  
        
         :      
        """
        total = len(chunks)
        for idx, chunk in enumerate(chunks):
            chunk['chunk_index'] = idx  # 0, 1, 2, ...
            chunk['chunk_total'] = total
        return chunks
    
    def _get_chunk_rules(self, chunk_type: str) -> Dict:
        """     """
        return CHUNK_PROCESSING_RULES.get(chunk_type, CHUNK_PROCESSING_RULES['default'])
    
    def _estimate_token_count(self, text: str) -> int:
        """
            
        
          :  1.5-2 = 1
         : 1.5 = 1
        
        Args:
            text:    
            
        Returns:
              
        """
        char_count = len(text)
        return int(char_count / 1.5)
    
    def _validate_token_limit(self, chunks: List[Dict], max_tokens: int = 512) -> Dict:
        """
            
        
        Args:
            chunks:   
            max_tokens:    (: 512)
            
        Returns:
            {
                'valid': bool,
                'violations': List[Dict],
                'stats': Dict
            }
        """
        violations = []
        token_counts = []
        
        for chunk in chunks:
            if chunk.get('drop', False):
                continue
            
            content = chunk.get('content', '')
            estimated_tokens = self._estimate_token_count(content)
            token_counts.append(estimated_tokens)
            
            if estimated_tokens > max_tokens:
                violations.append({
                    'chunk_id': chunk.get('chunk_id'),
                    'chunk_type': chunk.get('chunk_type'),
                    'char_count': len(content),
                    'estimated_tokens': estimated_tokens,
                    'excess_tokens': estimated_tokens - max_tokens
                })
        
        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'stats': {
                'total_chunks': len([c for c in chunks if not c.get('drop', False)]),
                'avg_tokens': sum(token_counts) / len(token_counts) if token_counts else 0,
                'max_tokens': max(token_counts) if token_counts else 0,
                'violation_count': len(violations),
                'violation_rate': len(violations) / len(token_counts) if token_counts else 0
            }
        }
    
    def _group_sentences(self, sentences: List[str], target_size: int) -> List[str]:
        """
            
        
        Args:
            sentences:   ( )
            target_size:  
            
        Returns:
              
        """
        grouped = []
        current_group = []
        current_length = 0
        
        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            sentence_length = len(sentence)
            
            if current_length + sentence_length > target_size and current_group:
                #   
                grouped.append(''.join(current_group))
                current_group = []
                current_length = 0
            
            current_group.append(sentence)
            current_length += sentence_length
            i += 1
        
        #   
        if current_group:
            grouped.append(''.join(current_group))
        
        return grouped
    
    def _split_chunk_semantic(self, chunk: Dict, rules: Dict) -> List[Dict]:
        """
             ()
        
         :
        1.   ( )
        2.   (, , )
        3. /
        
        Args:
            chunk:  
            rules:  
            
        Returns:
              
        """
        import re
        
        content = chunk.get('content', '')
        target_size = rules.get('target_length', 600)
        max_size = rules.get('max_length', 700)
        
        # 1:   
        sections = re.split(r'\n\n+', content)
        
        # 2:       
        refined_sections = []
        for section in sections:
            if len(section) > max_size:
                #    ( )
                sentences = re.split(r'([.!?]\s+)', section)
                grouped = self._group_sentences(sentences, target_size)
                refined_sections.extend(grouped)
            else:
                refined_sections.append(section)
        
        #     (  )
        return self._regroup_sections(chunk, refined_sections, rules)
    
    def _extract_sentences(self, text: str) -> List[str]:
        """
            ()
        
        Args:
            text:  
            
        Returns:
             
        """
        import re
        
        #    ( )
        # , ,  + /
        parts = re.split(r'([.!?](?:\s+|\n+))', text)
        
        #    
        sentences = []
        for i in range(0, len(parts)-1, 2):
            if i+1 < len(parts):
                sentence = parts[i] + parts[i+1]
                sentences.append(sentence.strip())
        
        #    (  )
        if len(parts) % 2 == 1 and parts[-1].strip():
            sentences.append(parts[-1].strip())
        
        return [s for s in sentences if s]
    
    def _get_sentence_overlap(self, sentences: List[str], overlap_size: int) -> str:
        """
          overlap   ()
        
        Args:
            sentences:  
            overlap_size:  overlap  ( )
            
        Returns:
            overlap 
        """
        if not sentences:
            return ""
        
        #    overlap_size 
        overlap_sentences = []
        current_length = 0
        
        for sentence in reversed(sentences):
            sentence_length = len(sentence)
            if current_length + sentence_length > overlap_size and overlap_sentences:
                break
            overlap_sentences.insert(0, sentence)
            current_length += sentence_length
        
        return ' '.join(overlap_sentences)
    
    def _validate_chunk_quality(self, content: str) -> tuple[bool, str]:
        """
           ()
        
         :
        1.   (  )
        2.   
        3.   
        
        Args:
            content:  
            
        Returns:
            (is_valid, reason):   
        """
        if not content or not content.strip():
            return False, " "
        
        content = content.strip()
        
        # 1.    (20 )
        if len(content) < 20:
            return False, f"   ({len(content)})"
        
        # 2.   
        import re
        text_only = re.sub(r'[^-a-zA-Z0-9]', '', content)
        if len(text_only) < 10:
            return False, "   "
        
        # 3.    (    )
        last_char = content[-1]
        sentence_enders = ['.', '!', '?', '', '', '', '', '', '', '']
        
        #      (but valid)
        if last_char not in sentence_enders:
            #    
            pass
        
        return True, ""
    
    def _regroup_sections(self, chunk: Dict, sections: List[str], rules: Dict) -> List[Dict]:
        """
             Overlapping  ()
        
        :
        -   Overlapping
        -   
        
        Args:
            chunk:  
            sections:   
            rules:  
            
        Returns:
               (overlap )
        """
        target_size = rules.get('target_length', 600)
        max_size = rules.get('max_length', 700)
        overlap_size = rules.get('overlap_size', 150)
        overlap_mode = rules.get('overlap_mode', 'char')  # 'char' or 'sentence'
        
        sub_chunks = []
        current_buffer = []
        current_length = 0
        previous_sentences = []  #    (sentence mode)
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            section_length = len(section)
            
            #       
            if current_length + section_length > target_size and current_buffer:
                #    
                chunk_content = '\n\n'.join(current_buffer)
                
                # Overlapping 
                if previous_sentences and sub_chunks:
                    if overlap_mode == 'sentence':
                        #   overlap ()
                        overlap_text = self._get_sentence_overlap(previous_sentences, overlap_size)
                        if overlap_text:
                            chunk_content = overlap_text + '\n\n' + chunk_content
                    else:
                        #    overlap
                        overlap_text = chunk_content[:overlap_size] if len(chunk_content) > overlap_size else chunk_content
                        if overlap_text:
                            chunk_content = overlap_text + '\n\n' + chunk_content
                
                #   ()
                is_valid, reason = self._validate_chunk_quality(chunk_content)
                if not is_valid:
                    #      
                    # (drop  -   )
                    if not chunk.get('metadata'):
                        chunk['metadata'] = {}
                    chunk['metadata']['quality_warning'] = reason
                
                sub_chunks.append({
                    **chunk,
                    'content': chunk_content,
                    'content_length': len(chunk_content),
                    'chunk_id': f"{chunk['chunk_id']}_part{len(sub_chunks)+1}",
                    'parent_chunk_id': chunk.get('chunk_id'),
                    'metadata': {
                        **chunk.get('metadata', {}),
                        'is_split': True,
                        'part_number': len(sub_chunks) + 1
                    }
                })
                
                #  overlap     
                previous_sentences = self._extract_sentences(chunk_content)
                
                #  
                current_buffer = []
                current_length = 0
            
            current_buffer.append(section)
            current_length += section_length + 2  # \n\n 
        
        #   
        if current_buffer:
            chunk_content = '\n\n'.join(current_buffer)
            if previous_sentences and sub_chunks:
                if overlap_mode == 'sentence':
                    overlap_text = self._get_sentence_overlap(previous_sentences, overlap_size)
                    if overlap_text:
                        chunk_content = overlap_text + '\n\n' + chunk_content
                else:
                    overlap_text = chunk_content[:overlap_size] if len(chunk_content) > overlap_size else chunk_content
                    if overlap_text:
                        chunk_content = overlap_text + '\n\n' + chunk_content
            
            #  
            is_valid, reason = self._validate_chunk_quality(chunk_content)
            if not is_valid:
                if not chunk.get('metadata'):
                    chunk['metadata'] = {}
                chunk['metadata']['quality_warning'] = reason
            
            sub_chunks.append({
                **chunk,
                'content': chunk_content,
                'content_length': len(chunk_content),
                'chunk_id': f"{chunk['chunk_id']}_part{len(sub_chunks)+1}" if sub_chunks else chunk['chunk_id'],
                'parent_chunk_id': chunk.get('chunk_id') if sub_chunks else None,
                'metadata': {
                    **chunk.get('metadata', {}),
                    'is_split': True if sub_chunks else False,
                    'part_number': len(sub_chunks) + 1 if sub_chunks else 1
                }
            })
        
        return sub_chunks if sub_chunks else [chunk]
    
    def _merge_short_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
          /  
        
        Args:
            chunks:  
            
        Returns:
              
        """
        if not chunks:
            return chunks
        
        merged = []
        buffer = []
        
        for i, chunk in enumerate(chunks):
            content = chunk.get('content', '')
            chunk_type = chunk.get('chunk_type', 'default')
            rules = self._get_chunk_rules(chunk_type)
            
            # drop=True   
            if chunk.get('drop', False):
                if buffer:
                    #     merged  
                    if merged:
                        last_chunk = merged[-1]
                        buffer_content = "\n\n".join([c['content'] for c in buffer])
                        last_chunk['content'] = last_chunk['content'] + "\n\n" + buffer_content
                        last_chunk['content_length'] = len(last_chunk['content'])
                    else:
                        # merged    
                        merged.extend(buffer)
                    buffer = []
                merged.append(chunk)
                continue
            
            #        
            if not rules['merge_allowed'] or len(content) >= rules['min_length']:
                #     
                if buffer:
                    merged_content = "\n\n".join([c['content'] for c in buffer] + [content])
                    chunk['content'] = merged_content
                    chunk['content_length'] = len(merged_content)
                    buffer = []
                merged.append(chunk)
            else:
                #    
                buffer.append(chunk)
        
        #   
        if buffer:
            if merged:
                #   
                last_chunk = merged[-1]
                buffer_content = "\n\n".join([c['content'] for c in buffer])
                last_chunk['content'] = last_chunk['content'] + "\n\n" + buffer_content
                last_chunk['content_length'] = len(last_chunk['content'])
            else:
                # merged     
                merged.extend(buffer)
        
        return merged
    
    def _split_long_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
             (  )
        
        Args:
            chunks:  
            
        Returns:
              
        """
        result = []
        
        for chunk in chunks:
            content = chunk.get('content', '')
            chunk_type = chunk.get('chunk_type', 'default')
            rules = self._get_chunk_rules(chunk_type)
            
            # drop=True   
            if chunk.get('drop', False):
                result.append(chunk)
                continue
            
            #       
            if not rules.get('split_allowed', False) or len(content) <= rules.get('max_length', 700):
                result.append(chunk)
                continue
            
            #     
            sub_chunks = self._split_chunk_semantic(chunk, rules)
            result.extend(sub_chunks)
        
        return result
    
    def _optimize_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
          ( +  + )
        
        Args:
            chunks:  
            
        Returns:
              
        """
        # 1.   
        chunks = self._merge_short_chunks(chunks)
        
        # 2.    ( )
        chunks = self._split_long_chunks(chunks)
        
        # 3.   
        for chunk in chunks:
            content = chunk.get('content', '').strip()
            chunk_type = chunk.get('chunk_type', 'default')
            rules = self._get_chunk_rules(chunk_type)
            
            #   drop_if_empty True 
            if not content and rules.get('drop_if_empty', False):
                chunk['drop'] = True
        
        # 4.   
        validation_result = self._validate_token_limit(chunks)
        
        if not validation_result['valid']:
            print(f"       : {validation_result['stats']['violation_count']}")
            print(f"    : {validation_result['stats']['violation_rate']*100:.1f}%")
            
            #    (  )
            chunks = self._resplit_violations(chunks, validation_result['violations'])
            
            # 
            revalidation = self._validate_token_limit(chunks)
            if revalidation['valid']:
                print(f"    :   ")
            else:
                print(f"      {revalidation['stats']['violation_count']} ")
        
        return chunks
    
    def _resplit_violations(self, chunks: List[Dict], violations: List[Dict]) -> List[Dict]:
        """
            
        
        Args:
            chunks:  
            violations:   
            
        Returns:
              
        """
        violation_ids = {v['chunk_id'] for v in violations}
        result = []
        
        for chunk in chunks:
            if chunk['chunk_id'] in violation_ids:
                #     (target_length 50% )
                rules = self._get_chunk_rules(chunk.get('chunk_type', 'default'))
                adjusted_rules = {
                    **rules, 
                    'target_length': rules.get('target_length', 600) // 2,
                    'max_length': rules.get('max_length', 700) // 2
                }
                sub_chunks = self._split_chunk_semantic(chunk, adjusted_rules)
                result.extend(sub_chunks)
            else:
                result.append(chunk)
        
        return result
    
    def _validate_chunk_indices(self, doc_id: str, chunks: List[Dict]):
        """chunk_index """
        chunks_sorted = sorted(chunks, key=lambda x: x['chunk_index'])
        
        expected_indices = list(range(len(chunks)))
        actual_indices = [c['chunk_index'] for c in chunks_sorted]
        
        if expected_indices != actual_indices:
            raise ValueError(
                f" Invalid chunk_index for {doc_id}:\n"
                f"   Expected: {expected_indices}\n"
                f"   Actual: {actual_indices}"
            )
        
        for chunk in chunks:
            if chunk['chunk_total'] != len(chunks):
                raise ValueError(
                    f" Invalid chunk_total for {chunk.get('chunk_id', 'unknown')}:\n"
                    f"   Expected: {len(chunks)}\n"
                    f"   Actual: {chunk['chunk_total']}"
                )
            
            if chunk['chunk_index'] >= chunk['chunk_total']:
                raise ValueError(
                    f" chunk_index >= chunk_total for {chunk.get('chunk_id', 'unknown')}:\n"
                    f"   chunk_index: {chunk['chunk_index']}\n"
                    f"   chunk_total: {chunk['chunk_total']}"
                )
    
    def _enrich_document(self, doc_data: Dict) -> Dict:
        """     """
        if not self.enrich_metadata or not self.metadata_enricher:
            return doc_data
        
        enriched_count = 0
        for chunk in doc_data.get('chunks', []):
            # drop=True  
            if chunk.get('drop', False):
                continue
            
            #  
            self.metadata_enricher.enrich_chunk_metadata(chunk, extract_all=True)
            enriched_count += 1
        
        self.stats['enriched_chunks'] += enriched_count
        return doc_data
    
    def _save_json(self, data: Dict, filename: str):
        """  JSON  """
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"   : {output_path}")
    
    def transform_law_data(self, file_path: str) -> Dict:
        """
          
        -  :  (law_id)
        -  : /// (unit_id)
        """
        print(f"\n   : {file_path}")
        
        chunks_by_law = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                law_id = data['law_id']
                
                if law_id not in chunks_by_law:
                    chunks_by_law[law_id] = {
                        'doc_id': f"statute:{law_id}",
                        'doc_type': 'law',
                        'title': data['law_name'],
                        'source_org': 'statute',
                        'category_path': None,
                        'url': None,
                        'metadata': {'law_id': law_id},
                        'chunks': []
                    }
                
                #  
                chunk = {
                    'chunk_id': f"statute:{law_id}:{data['unit_id']}",
                    'chunk_type': data['unit_level'],
                    'content': f"[] {data['law_name']}\n[] {data['path']}\n\n{data['index_text']}",
                    'content_length': len(data['index_text']),
                    'drop': False,
                    'metadata': {
                        'unit_id': data['unit_id'],
                        'path': data['path'],
                        'article_no': data.get('article_no'),
                        'paragraph_no': data.get('paragraph_no')
                    }
                }
                chunks_by_law[law_id]['chunks'].append(chunk)
        
        #      0-based  
        result = {'documents': []}
        
        for law_id, doc_data in chunks_by_law.items():
            #  
            doc_data['chunks'] = self._optimize_chunks(doc_data['chunks'])
            
            # 0-based  
            doc_data['chunks'] = self._assign_chunk_indices(doc_data['chunks'])
            self._validate_chunk_indices(doc_data['doc_id'], doc_data['chunks'])
            
            #  
            doc_data = self._enrich_document(doc_data)
            
            result['documents'].append(doc_data)
            
            self.stats['documents'] += 1
            self.stats['chunks'] += len(doc_data['chunks'])
            
            print(f"   {doc_data['title']}: {len(doc_data['chunks'])}  ( )")
        
        return result
    
    def transform_law_single_file(self, file_path: str) -> Dict:
        """
          JSONL  PostgreSQL  
        (      )
        
        Args:
            file_path:  JSONL  
        
        Returns:
            {
                'documents': [...]
            }
        """
        from pathlib import Path
        
        file_name = Path(file_path).stem  # : "Consumer_Basic_Law_chunks"
        print(f"\n   : {file_name}")
        
        #   ( -> )
        law_name_map = {
            'Civil_Law_chunks': '',
            'Commercial_Law_chunks': '',
            'Consumer_Basic_Law_chunks': '',
            'E_Commerce_Consumer_Law_chunks': '',
            'Product_Liability_Law_chunks': '',
            'Terms_Regulation_Law_chunks': '',
            'Installment_Sales_Law_chunks': '',
            'Direct_Sales_Law_chunks': '',
            'Fair_Ads_Law_chunks': '',
            'Content_Industry_Promotion_Law_chunks': '',
            'E_Transaction_Law_chunks': ''
        }
        
        #  law_id 
        chunks_by_law = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                    
                data = json.loads(line)
                law_id = data['law_id']
                law_name = data['law_name']
                
                if law_id not in chunks_by_law:
                    # doc_id    (law_id )
                    doc_id = f"law:{file_name.lower()}"
                    
                    chunks_by_law[law_id] = {
                        'doc_id': doc_id,
                        'doc_type': 'law',
                        'title': law_name,
                        'source_org': 'statute',
                        'category_path': ['', law_name],
                        'url': None,
                        'collected_at': None,
                        'metadata': {
                            'law_id': law_id,
                            'law_name': law_name,
                            'file_name': file_name
                        },
                        'chunks': []
                    }
                
                #  
                chunk = {
                    'chunk_id': f"law:{file_name.lower()}::{data['unit_id']}",
                    'chunk_type': data['unit_level'],
                    'content': f"[] {law_name}\n[] {data['path']}\n\n{data['index_text']}",
                    'content_length': len(data['index_text']),
                    'drop': False,
                    'metadata': {
                        'unit_id': data['unit_id'],
                        'path': data['path'],
                        'article_no': data.get('article_no'),
                        'paragraph_no': data.get('paragraph_no')
                    }
                }
                chunks_by_law[law_id]['chunks'].append(chunk)
        
        #      0-based  
        result = {'documents': []}
        
        for law_id, doc_data in chunks_by_law.items():
            #  
            doc_data['chunks'] = self._optimize_chunks(doc_data['chunks'])
            
            # 0-based  
            doc_data['chunks'] = self._assign_chunk_indices(doc_data['chunks'])
            self._validate_chunk_indices(doc_data['doc_id'], doc_data['chunks'])
            
            #  
            doc_data = self._enrich_document(doc_data)
            
            result['documents'].append(doc_data)
            
            self.stats['documents'] += 1
            self.stats['chunks'] += len(doc_data['chunks'])
            
            print(f"   {doc_data['title']}: {len(doc_data['chunks'])} ")
        
        return result
    
    def transform_criteria_table1(self, file_path: str) -> Dict:
        """
           - table1 ( )
        -  :   
        -  :  
        """
        print(f"\n    (table1 - ): {file_path}")
        
        doc_id = 'criteria:table1'
        chunks = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                    
                data = json.loads(line)
                
                # embed_text content 
                content = data.get('embed_text', '')
                metadata_raw = data.get('metadata', {})
                
                # stable_id chunk_id 
                chunk_id = data.get('stable_id', f"{doc_id}::item{len(chunks):04d}")
                
                chunk = {
                    'chunk_id': chunk_id,
                    'chunk_type': 'item',
                    'content': content,
                    'content_length': len(content),
                    'drop': False,
                    'metadata': {
                        'item_name': metadata_raw.get('item_name', ''),
                        'category': metadata_raw.get('category', ''),
                        'industry': metadata_raw.get('industry', ''),
                        'item_group': metadata_raw.get('item_group', ''),
                        'aliases': metadata_raw.get('aliases', [])
                    }
                }
                chunks.append(chunk)
        
        #  
        document = {
            'doc_id': doc_id,
            'doc_type': 'criteria_item_list',
            'title': ' - ',
            'source_org': 'KCA',
            'category_path': ['', ''],
            'url': None,
            'collected_at': None,
            'metadata': {
                'table_type': 'table1',
                'item_count': len(chunks)
            },
            'chunks': []
        }
        
        #     
        document['chunks'] = self._optimize_chunks(chunks)
        document['chunks'] = self._assign_chunk_indices(document['chunks'])
        self._validate_chunk_indices(document['doc_id'], document['chunks'])
        
        #  
        document = self._enrich_document(document)
        
        self.stats['documents'] += 1
        self.stats['chunks'] += len(document['chunks'])
        
        print(f"   {len(document['chunks'])}  ")
        
        return {'documents': [document]}
    
    def transform_criteria_table3(self, file_path: str) -> Dict:
        """
           - table3 ()
        -  :   
        -  :   
        """
        print(f"\n    (table3 - ): {file_path}")
        
        doc_id = 'criteria:table3'
        chunks = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                    
                data = json.loads(line)
                
                # embed_text content 
                content = data.get('embed_text', '')
                metadata_raw = data.get('metadata', {})
                
                # stable_id chunk_id 
                chunk_id = data.get('stable_id', f"{doc_id}::warranty{len(chunks):04d}")
                
                chunk = {
                    'chunk_id': chunk_id,
                    'chunk_type': 'warranty',
                    'content': content,
                    'content_length': len(content),
                    'drop': False,
                    'metadata': metadata_raw
                }
                chunks.append(chunk)
        
        #  
        document = {
            'doc_id': doc_id,
            'doc_type': 'criteria_warranty',
            'title': ' - ',
            'source_org': 'KCA',
            'category_path': ['', ''],
            'url': None,
            'collected_at': None,
            'metadata': {
                'table_type': 'table3',
                'item_count': len(chunks)
            },
            'chunks': []
        }
        
        #     
        document['chunks'] = self._optimize_chunks(chunks)
        document['chunks'] = self._assign_chunk_indices(document['chunks'])
        self._validate_chunk_indices(document['doc_id'], document['chunks'])
        
        #  
        document = self._enrich_document(document)
        
        self.stats['documents'] += 1
        self.stats['chunks'] += len(document['chunks'])
        
        print(f"   {len(document['chunks'])}  ")
        
        return {'documents': [document]}
    
    def transform_criteria_table4(self, file_path: str) -> Dict:
        """
           - table4 ()
        -  :   
        -  :   
        """
        print(f"\n    (table4 - ): {file_path}")
        
        doc_id = 'criteria:table4'
        chunks = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                    
                data = json.loads(line)
                
                # embed_text content 
                content = data.get('embed_text', '')
                metadata_raw = data.get('metadata', {})
                
                # stable_id chunk_id 
                chunk_id = data.get('stable_id', f"{doc_id}::lifespan{len(chunks):04d}")
                
                chunk = {
                    'chunk_id': chunk_id,
                    'chunk_type': 'lifespan',
                    'content': content,
                    'content_length': len(content),
                    'drop': False,
                    'metadata': metadata_raw
                }
                chunks.append(chunk)
        
        #  
        document = {
            'doc_id': doc_id,
            'doc_type': 'criteria_lifespan',
            'title': ' - ',
            'source_org': 'KCA',
            'category_path': ['', ''],
            'url': None,
            'collected_at': None,
            'metadata': {
                'table_type': 'table4',
                'item_count': len(chunks)
            },
            'chunks': []
        }
        
        #     
        document['chunks'] = self._optimize_chunks(chunks)
        document['chunks'] = self._assign_chunk_indices(document['chunks'])
        self._validate_chunk_indices(document['doc_id'], document['chunks'])
        
        #  
        document = self._enrich_document(document)
        
        self.stats['documents'] += 1
        self.stats['chunks'] += len(document['chunks'])
        
        print(f"   {len(document['chunks'])}  ")
        
        return {'documents': [document]}
    
    def transform_criteria_table2(self, file_path: str) -> Dict:
        """
           - table2 ()
        -  :   
        -  :   (row_idx  0-based )
        """
        print(f"\n    (table2): {file_path}")
        
        doc_id = 'criteria:table2'
        chunks = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                
                # drop  
                if data.get('drop', False):
                    self.stats['skipped'] += 1
                    continue
                
                chunk = {
                    'chunk_id': data['chunk_id'],
                    'chunk_type': 'resolution_row',
                    'content': data['text'],
                    'content_length': len(data['text']),
                    'drop': False,
                    'metadata': {
                        'category': data.get('category'),
                        'item_group': data.get('item_group'),
                        'item': data.get('item'),
                        'dispute_type': data.get('dispute_type'),
                        'resolution': data.get('resolution'),
                        'laws': data.get('laws', [])
                    },
                    'category_path': [
                        data.get('category'),
                        data.get('item_group'),
                        data.get('item')
                    ] if data.get('category') else None
                }
                chunks.append(chunk)
        
        #  
        chunks = self._optimize_chunks(chunks)
        
        # 0-based  
        chunks = self._assign_chunk_indices(chunks)
        
        document = {
            'doc_id': doc_id,
            'doc_type': 'criteria_resolution',
            'title': ' -  ',
            'source_org': 'KCA',
            'category_path': None,
            'url': None,
            'metadata': {'source': 'table2'},
            'chunks': chunks
        }
        
        self._validate_chunk_indices(doc_id, chunks)
        
        #  
        document = self._enrich_document(document)
        
        self.stats['documents'] += 1
        self.stats['chunks'] += len(chunks)
        
        print(f"   {document['title']}: {len(chunks)}  ( )")
        
        return {'documents': [document]}
    
    def transform_mediation_kca(self, file_path: str) -> Dict:
        """
        KCA  
        -  :  (case_no)
        -  : chunk_type
        """
        print(f"\n    (KCA): {file_path}")
        
        cases = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                case_no = data['case_no']
                
                if case_no not in cases:
                    cases[case_no] = {
                        'doc_id': f"kca:mediation:{case_no}",
                        'doc_type': 'mediation_case',
                        'title': f"{case_no} ",
                        'source_org': 'KCA',
                        'category_path': None,
                        'url': None,
                        'metadata': {
                            'case_no': case_no,
                            'decision_date': data.get('decision_date'),
                            'agency': 'kca'
                        },
                        'chunks': []
                    }
                
                #  content drop=True  ( law  )
                content = data['text']
                is_empty = len(content.strip()) == 0
                
                chunk = {
                    'chunk_id': f"kca:mediation:{case_no}:{data['chunk_type']}:{len(cases[case_no]['chunks']):04d}",
                    'chunk_type': data['chunk_type'],
                    'content': content,
                    'content_length': len(content),
                    'drop': is_empty,  #  content drop
                    'metadata': {}
                }
                cases[case_no]['chunks'].append(chunk)
        
        #      0-based  
        result = {'documents': []}
        
        for case_no, case_data in cases.items():
            #  
            case_data['chunks'] = self._optimize_chunks(case_data['chunks'])
            
            # 0-based  
            case_data['chunks'] = self._assign_chunk_indices(case_data['chunks'])
            self._validate_chunk_indices(case_data['doc_id'], case_data['chunks'])
            
            #  
            case_data = self._enrich_document(case_data)
            
            result['documents'].append(case_data)
            
            self.stats['documents'] += 1
            self.stats['chunks'] += len(case_data['chunks'])
        
        print(f"   {len(cases)} ,  {sum(len(c['chunks']) for c in cases.values())}  ( )")
        
        return result
    
    def transform_mediation_ecmc(self, file_path: str) -> Dict:
        """ECMC  """
        print(f"\n    (ECMC): {file_path}")
        
        cases = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                case_no = data['case_no']
                
                if case_no not in cases:
                    cases[case_no] = {
                        'doc_id': f"ecmc:mediation:{case_no}",
                        'doc_type': 'mediation_case',
                        'title': f"{case_no} ",
                        'source_org': 'ECMC',
                        'category_path': None,
                        'url': None,
                        'metadata': {
                            'case_no': case_no,
                            'decision_date': data.get('decision_date'),
                            'agency': 'ecmc'
                        },
                        'chunks': []
                    }
                
                #  content drop=True 
                content = data['text']
                is_empty = len(content.strip()) == 0
                
                chunk = {
                    'chunk_id': f"ecmc:mediation:{case_no}:{data['chunk_type']}:{len(cases[case_no]['chunks']):04d}",
                    'chunk_type': data['chunk_type'],
                    'content': content,
                    'content_length': len(content),
                    'drop': data.get('drop', False) or is_empty,  #  drop    content
                    'metadata': {}
                }
                cases[case_no]['chunks'].append(chunk)
        
        #      0-based   (drop=true )
        result = {'documents': []}
        
        for case_no, case_data in cases.items():
            #  
            case_data['chunks'] = self._optimize_chunks(case_data['chunks'])
            
            # 0-based  
            case_data['chunks'] = self._assign_chunk_indices(case_data['chunks'])
            self._validate_chunk_indices(case_data['doc_id'], case_data['chunks'])
            
            #  
            case_data = self._enrich_document(case_data)
            
            result['documents'].append(case_data)
            
            self.stats['documents'] += 1
            self.stats['chunks'] += len(case_data['chunks'])
        
        print(f"   {len(cases)} ,  {sum(len(c['chunks']) for c in cases.values())}  ( )")
        
        return result
    
    def transform_counsel_case(self, file_path: str) -> Dict:
        """
         
        -  doc_id, chunk_id, chunk_index 
        -  
        """
        print(f"\n  : {file_path}")
        
        documents = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                doc_id = data['doc_id']
                
                if doc_id not in documents:
                    documents[doc_id] = {
                        'doc_id': doc_id,
                        'doc_type': 'counsel_case',
                        'title': data['title'],
                        'source_org': 'consumer.go.kr',
                        'category_path': data.get('category_path', []),
                        'url': data.get('metadata', {}).get('url'),
                        'metadata': data.get('metadata', {}),
                        'chunks': []
                    }
                
                chunk = {
                    'chunk_id': data['chunk_id'],
                    'chunk_index': data['chunk_index'],  #  0-based
                    'chunk_total': data['chunk_total'],
                    'chunk_type': 'qa_combined',
                    'content': data['text'],
                    'content_length': len(data['text']),
                    'drop': False,
                    'metadata': {}
                }
                documents[doc_id]['chunks'].append(chunk)
        
        #    
        result = {'documents': []}
        
        for doc_id, doc_data in documents.items():
            #  
            doc_data['chunks'] = self._optimize_chunks(doc_data['chunks'])
            
            #  
            doc_data['chunks'] = self._assign_chunk_indices(doc_data['chunks'])
            
            # 
            self._validate_chunk_indices(doc_id, doc_data['chunks'])
            
            #  
            doc_data = self._enrich_document(doc_data)
            
            result['documents'].append(doc_data)
            
            self.stats['documents'] += 1
            self.stats['chunks'] += len(doc_data['chunks'])
        
        print(f"   {len(documents)} ,  {sum(len(d['chunks']) for d in documents.values())}  ( )")
        
        return result
    
    def run_transformation(self):
        """   """
        print("=" * 80)
        print("  ")
        print("=" * 80)
        
        all_results = []
        
        # 1.   ( 1)
        print("\n" + "=" * 80)
        print("1.   ")
        print("=" * 80)
        
        law_file = DATA_DIR / 'law' / 'Civil_Law_chunks.jsonl'
        if law_file.exists():
            result = self.transform_law_data(str(law_file))
            self._save_json(result, 'law_civil_law.json')
            all_results.append(result)
        else:
            print(f"       : {law_file}")
            print(f"    : {Path.cwd()}")
        
        # 2.  
        print("\n" + "=" * 80)
        print("2.   ")
        print("=" * 80)
        
        table2_file = DATA_DIR / 'criteria' / 'table2_resolution_row_chunks.jsonl'
        if table2_file.exists():
            result = self.transform_criteria_table2(str(table2_file))
            self._save_json(result, 'criteria_table2.json')
            all_results.append(result)
        else:
            print(f"       : {table2_file}")
            print(f"    : {Path.cwd()}")
        
        # 3.  ()
        print("\n" + "=" * 80)
        print("3.  ")
        print("=" * 80)
        
        kca_file = DATA_DIR / 'dispute_resolution' / 'kca_final.jsonl'
        if kca_file.exists():
            result = self.transform_mediation_kca(str(kca_file))
            self._save_json(result, 'mediation_kca.json')
            all_results.append(result)
        else:
            print(f"       : {kca_file}")
            print(f"    : {Path.cwd()}")
        
        ecmc_file = DATA_DIR / 'dispute_resolution' / 'ecmc_final_rag_chunks_normalized.jsonl'
        if ecmc_file.exists():
            result = self.transform_mediation_ecmc(str(ecmc_file))
            self._save_json(result, 'mediation_ecmc.json')
            all_results.append(result)
        else:
            print(f"       : {ecmc_file}")
            print(f"    : {Path.cwd()}")
        
        # 4.  ( 1)
        print("\n" + "=" * 80)
        print("4.  ")
        print("=" * 80)
        
        counsel_file = DATA_DIR / 'compensation_case' / 'cs_114_chunks_v2.jsonl'
        if counsel_file.exists():
            result = self.transform_counsel_case(str(counsel_file))
            self._save_json(result, 'counsel_cs_114.json')
            all_results.append(result)
        else:
            print(f"       : {counsel_file}")
            print(f"    : {Path.cwd()}")
        
        #  
        print("\n" + "=" * 80)
        print("  ")
        print("=" * 80)
        print(f"  -  : {self.stats['documents']:,}")
        print(f"  -  : {self.stats['chunks']:,}")
        print(f"  - : {self.stats['skipped']:,}")
        if self.enrich_metadata:
            print(f"  -  : {self.stats['enriched_chunks']:,} ")
        print(f"  - : {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            print("\n :")
            for error in self.stats['errors']:
                print(f"  - {error}")
        
        #   
        summary = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'files': {
                'law': 1,
                'criteria': 1,
                'mediation': 2,
                'counsel': 1
            }
        }
        self._save_json(summary, 'transformation_summary.json')
        
        print(f"\n  !  {self.output_dir}/  .")
        
        return all_results
    
    def close(self):
        """ """
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

def main():
    """ """
    transformer = DataTransformer(
        use_db=False  #  JSON 
    )
    
    try:
        transformer.run_transformation()
    except Exception as e:
        print(f"\n  : {e}")
        import traceback
        traceback.print_exc()
    finally:
        transformer.close()

if __name__ == '__main__':
    main()
