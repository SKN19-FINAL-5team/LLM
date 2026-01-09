#!/usr/bin/env python3
"""
   

 JSON       
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

#      
SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/data_processing/
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # ddoksori_demo/
DATA_DIR = PROJECT_ROOT / "backend" / "data"

#     (data_transform_pipeline.py )
CHUNK_PROCESSING_RULES = {
    'decision': {
        'min_length': 50,
        'max_length': 800,
        'drop_if_empty': True
    },
    'reasoning': {
        'min_length': 100,
        'max_length': 1500,
    },
    'judgment': {
        'min_length': 200,
        'max_length': 1500,
    },
    'law': {
        'min_length': 30,
        'max_length': 2000,
        'drop_if_empty': True,
    },
    'law_reference': {
        'min_length': 20,
        'max_length': 2000,
        'drop_if_empty': True
    },
    'resolution_row': {
        'min_length': 50,
        'max_length': 2000,
    },
    'qa_combined': {
        'min_length': 100,
        'max_length': 1500,
    },
    #  
    'default': {
        'min_length': 100,
        'max_length': 1500,
        'drop_if_empty': True
    }
}

#    
CHUNK_PROCESSING_RULES = {
    'decision': {
        'min_length': 50,
        'max_length': 800,
        'merge_allowed': False,  #   
        'drop_if_empty': True,
        'description': ''
    },
    'reasoning': {
        'min_length': 100,
        'max_length': 1500,
        'merge_allowed': True,
        'split_allowed': True,
        'description': ' '
    },
    'judgment': {
        'min_length': 200,
        'max_length': 1500,
        'split_allowed': True,  #    
        'description': ' '
    },
    'law': {
        'min_length': 30,
        'max_length': 2000,
        'drop_if_empty': True,
        'enrich_with_metadata': True,  #   
        'description': ' '
    },
    'summary': {
        'min_length': 50,
        'max_length': 1000,
        'description': ''
    },
    'full_text': {
        'min_length': 100,
        'max_length': 2000,
        'split_allowed': True,
        'description': ''
    },
    'case_info': {
        'min_length': 30,
        'max_length': 1000,
        'description': ' '
    },
    'default': {
        'min_length': 50,
        'max_length': 1500,
        'description': ''
    }
}


def has_meaningful_content(content: str) -> bool:
    """   """
    if not content or not content.strip():
        return False
    
    #  
    cleaned = content.strip()
    
    # 1.   
    if len(cleaned) < 5:
        return False
    
    # 2.   
    meaningless_patterns = [
        r'^[-]\.$',  #   +  (: ".", ".")
        r'^[0-9]+\.$',   #  +  (: "1.", "2.")
        r'^[\s\n\r\t]+$',  # 
        r'^[-=_*#]+$',   # 
    ]
    
    for pattern in meaningless_patterns:
        if re.match(pattern, cleaned):
            return False
    
    # 3. /   5   
    text_chars = re.findall(r'[-a-zA-Z]', cleaned)
    if len(text_chars) < 5:
        return False
    
    return True


def estimate_token_count(text: str) -> int:
    """
       ( )
    
      :  1.5-2 = 1
     : 1.5 = 1
    
    Args:
        text:    
        
    Returns:
          
    """
    return int(len(text) / 1.5)


def validate_token_limits(chunks: List[Dict], max_tokens: int = 512) -> Dict:
    """
      
    
    Args:
        chunks:   
        max_tokens:    (: 512, KURE-v1  )
        
    Returns:
        {
            'violations': List[Dict],
            'stats_by_type': Dict,
            'total_violations': int
        }
    """
    violations = []
    stats_by_type = defaultdict(lambda: {
        'count': 0,
        'avg_tokens': 0,
        'max_tokens': 0,
        'violation_count': 0
    })
    
    for chunk in chunks:
        if chunk.get('drop', False):
            continue
        
        chunk_type = chunk.get('chunk_type', 'unknown')
        content = chunk.get('content', '')
        estimated_tokens = estimate_token_count(content)
        
        stats = stats_by_type[chunk_type]
        stats['count'] += 1
        stats['avg_tokens'] = (stats['avg_tokens'] * (stats['count'] - 1) + estimated_tokens) / stats['count']
        stats['max_tokens'] = max(stats['max_tokens'], estimated_tokens)
        
        if estimated_tokens > max_tokens:
            stats['violation_count'] += 1
            violations.append({
                'chunk_id': chunk.get('chunk_id'),
                'chunk_type': chunk_type,
                'char_count': len(content),
                'estimated_tokens': estimated_tokens,
                'excess_tokens': estimated_tokens - max_tokens
            })
    
    return {
        'violations': violations,
        'stats_by_type': dict(stats_by_type),
        'total_violations': len(violations)
    }


def check_encoding_quality(content: str) -> Tuple[bool, str]:
    """     """
    if not content:
        return False, " "
    
    try:
        # UTF-8   
        content.encode('utf-8')
    except UnicodeEncodeError as e:
        return False, f"UTF-8  : {e}"
    
    #     (    )
    total_chars = len(content)
    if total_chars == 0:
        return False, " "
    
    #   (, , , ,  )
    normal_chars = len(re.findall(r'[-a-zA-Z0-9\s.,!?;:()\[\]{}"\'-]', content))
    normal_ratio = normal_chars / total_chars
    
    if normal_ratio < 0.8:  #   80%  
        return False, f"    ({normal_ratio:.1%})"
    
    return True, ""

class TransformedDataValidator:
    """  """
    
    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = DATA_DIR / "transformed"
        self.data_dir = Path(data_dir)
        self.issues = []
        self.warnings = []
        self.stats = defaultdict(int)
    
    def load_all_data(self) -> Dict[str, Dict]:
        """  JSON  """
        data = {}
        
        json_files = list(self.data_dir.glob('*.json'))
        if not json_files:
            print(f" {self.data_dir} JSON  .")
            return data
        
        for json_file in json_files:
            if json_file.name == 'transformation_summary.json':
                continue
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data[json_file.stem] = json.load(f)
                print(f" : {json_file.name}")
            except Exception as e:
                print(f"  : {json_file.name} - {e}")
        
        return data
    
    def validate_chunk_indices(self, doc_data: Dict) -> bool:
        """chunk_index """
        doc_id = doc_data['doc_id']
        chunks = doc_data['chunks']
        
        is_valid = True
        
        # 1. chunk_index 0 
        min_index = min(c['chunk_index'] for c in chunks)
        if min_index != 0:
            self.issues.append(
                f" {doc_id}: chunk_index 0   (: {min_index})"
            )
            is_valid = False
        
        # 2. chunk_index 
        indices = sorted(c['chunk_index'] for c in chunks)
        expected_indices = list(range(len(chunks)))
        if indices != expected_indices:
            self.issues.append(
                f" {doc_id}: chunk_index  \n"
                f"   Expected: {expected_indices}\n"
                f"   Actual: {indices}"
            )
            is_valid = False
        
        # 3. chunk_total 
        for chunk in chunks:
            if chunk['chunk_total'] != len(chunks):
                self.issues.append(
                    f" {doc_id}: chunk_total \n"
                    f"   chunk_id: {chunk['chunk_id']}\n"
                    f"   Expected: {len(chunks)}\n"
                    f"   Actual: {chunk['chunk_total']}"
                )
                is_valid = False
                break
        
        # 4. chunk_index < chunk_total 
        for chunk in chunks:
            if chunk['chunk_index'] >= chunk['chunk_total']:
                self.issues.append(
                    f" {doc_id}: chunk_index >= chunk_total\n"
                    f"   chunk_id: {chunk['chunk_id']}\n"
                    f"   chunk_index: {chunk['chunk_index']}\n"
                    f"   chunk_total: {chunk['chunk_total']}"
                )
                is_valid = False
                break
        
        return is_valid
    
    def validate_required_fields(self, doc_data: Dict) -> bool:
        """  """
        doc_id = doc_data['doc_id']
        is_valid = True
        
        #   
        doc_required = ['doc_id', 'doc_type', 'title', 'source_org', 'chunks']
        for field in doc_required:
            if field not in doc_data:
                self.issues.append(f" {doc_id}:  '{field}'  ")
                is_valid = False
        
        #   
        chunk_required = ['chunk_id', 'chunk_index', 'chunk_total', 'chunk_type', 'content', 'content_length', 'drop']
        for chunk in doc_data.get('chunks', []):
            for field in chunk_required:
                if field not in chunk:
                    self.issues.append(
                        f" {doc_id}:  {chunk.get('chunk_id', 'unknown')} '{field}'  "
                    )
                    is_valid = False
                    break
        
        return is_valid
    
    def validate_content_quality(self, doc_data: Dict) -> bool:
        """   """
        doc_id = doc_data['doc_id']
        is_valid = True
        
        for chunk in doc_data.get('chunks', []):
            content = chunk.get('content', '')
            content_length = chunk.get('content_length', 0)
            chunk_type = chunk.get('chunk_type', 'default')
            chunk_id = chunk.get('chunk_id', 'unknown')
            should_drop = chunk.get('drop', False)
            
            #    
            rules = CHUNK_PROCESSING_RULES.get(chunk_type, CHUNK_PROCESSING_RULES['default'])
            min_length = rules['min_length']
            max_length = rules['max_length']
            
            # 1.    (Critical)
            if not content or not content.strip():
                # drop=True  
                if should_drop:
                    self.stats[f'dropped_empty_{chunk_type}'] += 1
                elif rules.get('drop_if_empty', False):
                    self.warnings.append(
                        f"  {doc_id}:  content (drop=True  )\n"
                        f"   chunk_id: {chunk_id}\n"
                        f"   chunk_type: {chunk_type}"
                    )
                else:
                    self.issues.append(
                        f" {doc_id}: content \n"
                        f"   chunk_id: {chunk_id}\n"
                        f"   chunk_type: {chunk_type}"
                    )
                    is_valid = False
                continue
            
            # 2.    (Critical)
            encoding_ok, encoding_msg = check_encoding_quality(content)
            if not encoding_ok:
                self.issues.append(
                    f" {doc_id}:  \n"
                    f"   chunk_id: {chunk_id}\n"
                    f"   : {encoding_msg}"
                )
                is_valid = False
                continue
            
            # 3.    
            if not has_meaningful_content(content):
                if should_drop:
                    self.stats[f'dropped_meaningless_{chunk_type}'] += 1
                else:
                    self.warnings.append(
                        f"  {doc_id}:    (drop=True )\n"
                        f"   chunk_id: {chunk_id}\n"
                        f"   content: {content[:100]}"
                    )
            
            # 4.    
            if content_length < min_length and not should_drop:
                severity = "" if rules.get('merge_allowed', False) else ""
                self.warnings.append(
                    f"  {doc_id}:     ({severity})\n"
                    f"   chunk_id: {chunk_id}\n"
                    f"   chunk_type: {chunk_type} (: {min_length})\n"
                    f"    : {content_length}\n"
                    f"   : {content[:100]}"
                )
                self.stats[f'too_short_{chunk_type}'] += 1
            
            # 5.    
            if content_length > max_length:
                severity = "" if rules.get('split_allowed', False) else ""
                self.warnings.append(
                    f"  {doc_id}:     ({severity} )\n"
                    f"   chunk_id: {chunk_id}\n"
                    f"   chunk_type: {chunk_type} (: {max_length})\n"
                    f"    : {content_length:,}"
                )
                self.stats[f'too_long_{chunk_type}'] += 1
            
            # 6. content_length   
            actual_length = len(content)
            if abs(actual_length - content_length) > 5:  # 5  
                self.warnings.append(
                    f"  {doc_id}: content_length \n"
                    f"   chunk_id: {chunk_id}\n"
                    f"   Expected: {content_length}\n"
                    f"   Actual: {actual_length}"
                )
            
            # 7. RAG    (100-2000)
            if not should_drop:
                if 100 <= content_length <= 2000:
                    self.stats['optimal_chunks'] += 1
                elif content_length < 100:
                    self.stats['suboptimal_too_short'] += 1
                else:
                    self.stats['suboptimal_too_long'] += 1
        
        return is_valid
    
    def validate_document(self, doc_data: Dict) -> bool:
        """  """
        doc_id = doc_data.get('doc_id', 'unknown')
        
        # 1.   
        if not self.validate_required_fields(doc_data):
            return False
        
        # 2. chunk_index 
        if not self.validate_chunk_indices(doc_data):
            return False
        
        # 3.   
        if not self.validate_content_quality(doc_data):
            return False
        
        #  
        self.stats['total_documents'] += 1
        self.stats['total_chunks'] += len(doc_data.get('chunks', []))
        self.stats[f"doc_type_{doc_data['doc_type']}"] += 1
        self.stats[f"source_org_{doc_data['source_org']}"] += 1
        
        return True
    
    def validate_all(self, data: Dict[str, Dict]) -> Tuple[bool, Dict]:
        """  """
        print("\n" + "=" * 80)
        print("   ")
        print("=" * 80)
        
        all_valid = True
        
        for file_name, file_data in data.items():
            print(f"\n : {file_name}")
            
            documents = file_data.get('documents', [])
            print(f"  -  : {len(documents)}")
            
            for doc_data in documents:
                doc_valid = self.validate_document(doc_data)
                if not doc_valid:
                    all_valid = False
        
        #   
        print("\n    (KURE-v1 : 512 )")
        all_chunks = []
        for file_name, file_data in data.items():
            for doc_data in file_data.get('documents', []):
                all_chunks.extend(doc_data.get('chunks', []))
        
        token_validation = validate_token_limits(all_chunks)
        
        print(f"  -  : {len([c for c in all_chunks if not c.get('drop', False)]):,}")
        print(f"  -  : {token_validation['total_violations']:,}")
        
        if token_validation['total_violations'] > 0:
            print(f"\n        :")
            for chunk_type, stats in sorted(token_validation['stats_by_type'].items()):
                if stats['violation_count'] > 0:
                    violation_rate = stats['violation_count'] / stats['count'] * 100
                    print(f"    • {chunk_type}: {stats['violation_count']}/{stats['count']} ({violation_rate:.1f}%)")
                    print(f"      -  : {stats['avg_tokens']:.0f}")
                    print(f"      -  : {stats['max_tokens']:.0f}")
        else:
            print(f"       ")
        
        #  
        print("\n" + "=" * 80)
        print(" ")
        print("=" * 80)
        
        print(f"\n  :")
        print(f"  -  : {self.stats['total_documents']:,}")
        print(f"  -  : {self.stats['total_chunks']:,}")
        
        # RAG  
        optimal = self.stats.get('optimal_chunks', 0)
        too_short = self.stats.get('suboptimal_too_short', 0)
        too_long = self.stats.get('suboptimal_too_long', 0)
        total_checked = optimal + too_short + too_long
        
        if total_checked > 0:
            print(f"\n RAG   (100-2000 ):")
            print(f"  -  : {optimal:,} ({optimal/total_checked*100:.1f}%)")
            print(f"  -  : {too_short:,} ({too_short/total_checked*100:.1f}%)")
            print(f"  -  : {too_long:,} ({too_long/total_checked*100:.1f}%)")
        
        #    
        print(f"\n    :")
        type_issues = {}
        for key in self.stats:
            if key.startswith('too_short_') or key.startswith('too_long_'):
                parts = key.split('_', 2)
                issue_type = parts[0] + '_' + parts[1]
                chunk_type = parts[2] if len(parts) > 2 else 'unknown'
                
                if chunk_type not in type_issues:
                    type_issues[chunk_type] = {'too_short': 0, 'too_long': 0}
                
                if issue_type == 'too_short':
                    type_issues[chunk_type]['too_short'] = self.stats[key]
                elif issue_type == 'too_long':
                    type_issues[chunk_type]['too_long'] = self.stats[key]
        
        for chunk_type, issues in sorted(type_issues.items()):
            rules = CHUNK_PROCESSING_RULES.get(chunk_type, CHUNK_PROCESSING_RULES['default'])
            desc = rules['description']
            if issues['too_short'] > 0 or issues['too_long'] > 0:
                print(f"  - {desc} ({chunk_type}):")
                if issues['too_short'] > 0:
                    print(f"    •  : {issues['too_short']:,}")
                if issues['too_long'] > 0:
                    print(f"    •  : {issues['too_long']:,}")
        
        print(f"\n :")
        print(f"  -  Critical : {len(self.issues)}")
        print(f"  -   : {len(self.warnings)}")
        
        if self.issues:
            print(f"\n Critical   ( 10):")
            for issue in self.issues[:10]:
                print(f"  {issue}")
            if len(self.issues) > 10:
                print(f"  ...  {len(self.issues) - 10}")
        
        if self.warnings:
            print(f"\n    ( 5):")
            for warning in self.warnings[:5]:
                print(f"  {warning}")
            if len(self.warnings) > 5:
                print(f"  ...  {len(self.warnings) - 5}")
        
        #  
        if too_short > total_checked * 0.1:  # 10%    
            print(f"\n  :")
            print(f"  -     (data_transform_pipeline.py )")
        
        if too_long > total_checked * 0.05:  # 5%    
            print(f"  -     (data_transform_pipeline.py )")
        
        print("\n" + "=" * 80)
        if all_valid and not self.issues:
            print("  !   .")
            if self.warnings:
                print("   (    )")
        else:
            print("  ! Critical     .")
        print("=" * 80)
        
        return all_valid, dict(self.stats)
    
    def show_sample_data(self, data: Dict[str, Dict], n: int = 2):
        """  """
        print("\n" + "=" * 80)
        print("  ")
        print("=" * 80)
        
        for file_name, file_data in data.items():
            documents = file_data.get('documents', [])[:n]
            
            for doc in documents:
                print(f"\n [{doc['doc_type']}] {doc['doc_id']}")
                print(f"  : {doc['title']}")
                print(f"  : {doc['source_org']}")
                print(f"   : {len(doc['chunks'])}")
                
                #    
                if doc['chunks']:
                    chunk = doc['chunks'][0]
                    print(f"\n  [ 0] {chunk['chunk_id']}")
                    print(f"    : {chunk['chunk_type']}")
                    print(f"    : {chunk['chunk_index']}/{chunk['chunk_total']}")
                    print(f"    : {chunk['content_length']}")
                    print(f"    drop: {chunk['drop']}")
                    content_preview = chunk['content'][:200].replace('\n', ' ')
                    print(f"    : {content_preview}...")

def main():
    """ """
    validator = TransformedDataValidator()
    
    # 1.  
    print("=" * 80)
    print("  ")
    print("=" * 80)
    data = validator.load_all_data()
    
    if not data:
        print("\n   .")
        print(" data_transform_pipeline.py .")
        return
    
    print(f"\n {len(data)}   ")
    
    # 2.   
    validator.show_sample_data(data, n=1)
    
    # 3. 
    all_valid, stats = validator.validate_all(data)
    
    # 4.  
    result = {
        'valid': all_valid and not validator.issues,
        'issues_count': len(validator.issues),
        'warnings_count': len(validator.warnings),
        'issues': validator.issues,
        'warnings': validator.warnings,
        'stats': stats
    }
    
    output_path = validator.data_dir / 'validation_result.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n   : {output_path}")
    
    return 0 if result['valid'] else 1

if __name__ == '__main__':
    exit(main())
