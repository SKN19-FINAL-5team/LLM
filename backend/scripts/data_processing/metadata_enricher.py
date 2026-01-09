#!/usr/bin/env python3
"""
  

 content   :
1.  ( )
2.  (,  )
3.  
4.  
"""

import re
from typing import Dict, List, Set
from collections import Counter


class MetadataEnricher:
    """  """
    
    def __init__(self):
        #   
        self.legal_terms = {
            '', '', '', '', '', '', '', '',
            '', '', '', '', '', '',
            '', '', '', '', '', '', '',
            '', '', '', '', '', '', '',
            '', '', '', '', '', '', '', '',
            '', '', '', '', '', '', '', '', ''
        }
        
        #   
        self.category_keywords = {
            '': ['', '', '', '', '', '', '', ''],
            '': ['', '', '', '', '', '', ''],
            '': ['', '', '', '', '', '', ''],
            '': ['', 'TV', '', '', '', ''],
            '': ['', '', '', '', '', '', ''],
            '': ['', '', '', '', ''],
            '': ['', '', '', '', '', ''],
            '': ['', '', '', '', '', ''],
            '': ['', '', '', '', '', ''],
            '': ['', '', '', '', ''],
            '': ['', '', '', '', '', '']
        }
        
        # /  (  )
        self.product_patterns = [
            r'\s?\d+(?:\s?)?',  #  14,  15 
            r'\s?[A-Z]?\d+(?:\s?[|])?',  #  S24,  S24 
            r'(?:|TV||||)(?:\s?[-0-9]+)?',  # 
            r'LG\s?[A-Z0-9]+',  # LG 
            r'Samsung\s?[A-Z0-9]+',  # Samsung 
        ]
        
        #  
        self.company_patterns = [
            r'(?:|)\s?[-]+',
            r'[-]+(?:|)',
            r'[-]+\s?(?:|Korea)',
            r'[A-Z][a-z]+\s?(?:Korea|)',
        ]
        
        #  (   )
        self.stopwords = {
            '', '', '', '', '', '', '', '', '', '',
            '', '', '', '', '', '', '', '',
            '', '', '', '', '', '', '', '', '', ''
        }
    
    def extract_keywords(self, content: str, top_k: int = 10) -> List[str]:
        """
          ( )
        
        Args:
            content:  
            top_k:   
        
        Returns:
             
        """
        # ,   (2 )
        words = re.findall(r'[-]{2,}|[A-Za-z]{3,}', content)
        
        #  
        words = [w for w in words if w not in self.stopwords]
        
        #  
        word_counts = Counter(words)
        
        #  k 
        keywords = [word for word, count in word_counts.most_common(top_k)]
        
        return keywords
    
    def extract_entities(self, content: str) -> Dict[str, List[str]]:
        """
          (, )
        
        Args:
            content:  
        
        Returns:
              {'companies': [...], 'products': [...]}
        """
        entities = {
            'companies': [],
            'products': []
        }
        
        #  
        for pattern in self.company_patterns:
            matches = re.findall(pattern, content)
            entities['companies'].extend(matches)
        
        #  
        for pattern in self.product_patterns:
            matches = re.findall(pattern, content)
            entities['products'].extend(matches)
        
        #  
        entities['companies'] = list(set(entities['companies']))
        entities['products'] = list(set(entities['products']))
        
        return entities
    
    def extract_legal_terms(self, content: str) -> List[str]:
        """
          
        
        Args:
            content:  
        
        Returns:
              
        """
        found_terms = []
        
        for term in self.legal_terms:
            if term in content:
                found_terms.append(term)
        
        return found_terms
    
    def infer_category(self, content: str) -> List[str]:
        """
          ( )
        
        Args:
            content:  
        
        Returns:
             
        """
        categories = []
        
        for category, keywords in self.category_keywords.items():
            #     
            match_count = sum(1 for kw in keywords if kw in content)
            
            # 2     
            if match_count >= 2:
                categories.append(category)
        
        return categories
    
    def extract_law_references(self, content: str) -> List[str]:
        """
           (: " 750", " 16")
        
        Args:
            content:  
        
        Returns:
              
        """
        # :  +  +  + 
        pattern = r'[-]+\s?\s?\d+(?:\s?\s?\d+)?'
        matches = re.findall(pattern, content)
        
        return list(set(matches))
    
    def extract_dates(self, content: str) -> List[str]:
        """
          (YYYY-MM-DD, YYYY.MM.DD )
        
        Args:
            content:  
        
        Returns:
             
        """
        patterns = [
            r'\d{4}[-./]\d{1,2}[-./]\d{1,2}',  # 2024-01-15
            r'\d{4}\s?\d{1,2}\s?\d{1,2}',  # 2024 1 15
        ]
        
        dates = []
        for pattern in patterns:
            matches = re.findall(pattern, content)
            dates.extend(matches)
        
        return list(set(dates))
    
    def enrich_chunk_metadata(self, chunk: Dict, extract_all: bool = True) -> Dict:
        """
          
        
        Args:
            chunk:  
            extract_all:    
        
        Returns:
              
        """
        content = chunk.get('content', '')
        
        if not content or not content.strip():
            return chunk
        
        #    (  )
        metadata = chunk.get('metadata', {})
        
        if extract_all:
            # 1.  
            keywords = self.extract_keywords(content, top_k=10)
            if keywords:
                metadata['keywords'] = keywords
            
            # 2.  
            entities = self.extract_entities(content)
            if entities['companies'] or entities['products']:
                metadata['entities'] = entities
            
            # 3.   
            legal_terms = self.extract_legal_terms(content)
            if legal_terms:
                metadata['legal_terms'] = legal_terms
            
            # 4.  
            categories = self.infer_category(content)
            if categories:
                metadata['category_tags'] = categories
            
            # 5.   
            law_refs = self.extract_law_references(content)
            if law_refs:
                metadata['law_references'] = law_refs
            
            # 6.  
            dates = self.extract_dates(content)
            if dates:
                metadata['dates'] = dates
        
        #  
        chunk['metadata'] = metadata
        
        return chunk
    
    def enrich_document_metadata(self, doc_data: Dict, extract_all: bool = True) -> Dict:
        """
             
        
        Args:
            doc_data:  
            extract_all:    
        
        Returns:
              
        """
        for chunk in doc_data.get('chunks', []):
            self.enrich_chunk_metadata(chunk, extract_all=extract_all)
        
        return doc_data


def test_enricher():
    """ """
    enricher = MetadataEnricher()
    
    #  
    test_chunk = {
        'chunk_id': 'test:001',
        'chunk_type': 'judgment',
        'content': '''
             S24   
             .
         750      ,
         16    .
        2024 1 15  ,  2024.01.20 .
        ''',
        'content_length': 200,
        'drop': False
    }
    
    #  
    enriched = enricher.enrich_chunk_metadata(test_chunk)
    
    print("=" * 80)
    print("  ")
    print("=" * 80)
    print(f"\n  ID: {test_chunk['chunk_id']}")
    print(f" : {len(test_chunk['content'])}")
    
    metadata = enriched['metadata']
    
    print(f"\n  ({len(metadata.get('keywords', []))}):")
    for kw in metadata.get('keywords', []):
        print(f"  - {kw}")
    
    print(f"\n :")
    entities = metadata.get('entities', {})
    if entities.get('companies'):
        print(f"  : {', '.join(entities['companies'])}")
    if entities.get('products'):
        print(f"  : {', '.join(entities['products'])}")
    
    print(f"\n    ({len(metadata.get('legal_terms', []))}):")
    for term in metadata.get('legal_terms', [])[:10]:
        print(f"  - {term}")
    
    print(f"\n  :")
    for cat in metadata.get('category_tags', []):
        print(f"  - {cat}")
    
    print(f"\n  :")
    for ref in metadata.get('law_references', []):
        print(f"  - {ref}")
    
    print(f"\n :")
    for date in metadata.get('dates', []):
        print(f"  - {date}")


if __name__ == '__main__':
    test_enricher()
