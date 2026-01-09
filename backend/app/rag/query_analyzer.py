"""
Query Analyzer Module
      
"""

import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum


class QueryType(Enum):
    """ """
    LEGAL = "legal"               #   (, )
    PRACTICAL = "practical"       #   ( )
    PRODUCT_SPECIFIC = "product_specific"  #   
    GENERAL = "general"           #  


@dataclass
class QueryAnalysis:
    """  """
    query_type: QueryType
    extracted_items: List[str]       #  
    extracted_articles: List[Dict]   #   
    keywords: List[str]              #  
    dispute_types: List[str]         #  
    law_names: List[str]            # 
    has_amount: bool                #   
    has_date: bool                  #   


class QueryAnalyzer:
    """ """
    
    #  
    LEGAL_KEYWORDS = {
        '', '', '', '', '', '', '', '', '',
        '', '', '', '', '',
        '', '', '', ''
    }
    
    #  
    PRACTICAL_KEYWORDS = {
        '', '', '', '', '', '', '',
        '', '', '', '', '',
        '', '', ''
    }
    
    #    (Criteria    -  200+ )
    PRODUCT_KEYWORDS = {
        #  
        '', '', '', '', '',
        
        #  ()
        '', '', '', '', 'TV', '', '', '', 
        '', '', '', '', '', '', '',
        '', '', '', '', '', '',
        '', '', '', '', '', '', '',
        '', '', '', '', '', '', '',
        '', '', '', '', '', '',
        '', '', '', '', '', '',
        '', '', '', '', '', '',
        '', '', '', '', '', '',
        '', '', '', '', '', '', '',
        '', '', 'DVD', 'VTR', 'MP3', '',
        '', '', '', '', '', '',
        '', '', '', '', '', '',
        
        # 
        '', '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '',
        '', '', '', '',
        
        # /
        '', '', '', '', '', '', '', '', '', 
        '', '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '',
        '', '', '', '', '', '',
        '', '', '', '', '', '', '', '',
        '', '', '',
        '', '', '', '', '', '', '', '',
        '', '', '',
        '', '', '', '', '', '', '',
        
        # 
        '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '', '',
        '', '', '', '', '',
        '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '', '',
        
        # /
        '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '',
        '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', 
        '', '', '',
        
        # 
        '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '', '',
        '', '', '', '', '', '',
        '', '', '', '', '',
        '', '', '', '', '', '',
        
        # /
        '', '', '', '', '',
        '', '', '', '', '',
        '', '', '', '', '', '', 
        '', '', 'USB', '', 'SSD', '',
        
        # /
        '', '', '', '', '', '', 'SUV', '',
        '', '', '', '', '', '',
        '', '', '', '',
        
        # /
        '', '', '', '', '', '', '',
        '', '', '', '', '', '', '',
        '', '', '', '', '', '',
        '', '', '', '', '', '', '',
        
        # 
        '', '', '', '', '', '', '',
        '', '', '', '', '',
        '', '', '', '', '',
        '', '', '', '', '',
        '', '', '', '',
        '', '', '', '', '', '', '', '',
        '', '', '', '', '',
        '', '', '', '', '',
        '', '', '', '', '',
        '', '', '', '',
    }
    
    #    (  )
    PRODUCT_SYNONYMS = {
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        'PC': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': 'TV',
        '': 'TV',
        '': 'TV',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
    }
    
    #   
    DISPUTE_TYPE_KEYWORDS = {
        '': ['', '', '', '', ''],
        '': ['', '', '', ''],
        '': ['', 'A/S', 'AS', '', '', ''],
        '': ['', '', '', '', ''],
        '': ['', '', '', '', '', ''],
        '': ['', '', '', '', ''],
        '': ['', '', '', ''],
        '': ['', '', '', ''],
        '': ['', '', ''],
    }
    
    #  
    LAW_NAMES = [
        '', '', '', '', 
        '    ',
        '   ', '',
        '  ', '   ',
        ' ', '',
        '·   ',
        ' ', ''
    ]
    
    def __init__(self):
        """"""
        pass
    
    def analyze(self, query: str) -> QueryAnalysis:
        """
           
        
        Args:
            query:  
        
        Returns:
            QueryAnalysis 
        """
        query_lower = query.lower()
        
        # 1.   
        query_type = self._classify_query_type(query, query_lower)
        
        # 2.  
        extracted_articles = self._extract_law_articles(query)
        
        # 3.  
        extracted_items = self._extract_product_names(query, query_lower)
        
        # 4.  
        keywords = self._extract_keywords(query, query_lower)
        
        # 5.   
        dispute_types = self._infer_dispute_types(query, query_lower)
        
        # 6.  
        law_names = self._extract_law_names(query)
        
        # 7. /  
        has_amount = bool(re.search(r'\d+\s*?\s*', query))
        has_date = bool(re.search(r'\d{4}[.-]', query))
        
        return QueryAnalysis(
            query_type=query_type,
            extracted_items=extracted_items,
            extracted_articles=extracted_articles,
            keywords=keywords,
            dispute_types=dispute_types,
            law_names=law_names,
            has_amount=has_amount,
            has_date=has_date
        )
    
    def _classify_query_type(self, query: str, query_lower: str) -> QueryType:
        """
          
        
        :
        1.     → LEGAL
        2.  +  → PRODUCT_SPECIFIC
        3.    → PRACTICAL
        4.  → GENERAL
        """
        #   
        has_article = bool(re.search(r'\s*\d+\s*', query))
        
        #  
        has_law_name = any(law_name in query for law_name in self.LAW_NAMES)
        
        #   
        legal_count = sum(1 for kw in self.LEGAL_KEYWORDS if kw in query_lower)
        
        #   
        product_count = sum(1 for kw in self.PRODUCT_KEYWORDS if kw in query_lower)
        
        #   
        practical_count = sum(1 for kw in self.PRACTICAL_KEYWORDS if kw in query_lower)
        
        #    
        has_dispute_type = any(
            any(kw in query_lower for kw in keywords)
            for keywords in self.DISPUTE_TYPE_KEYWORDS.values()
        )
        
        #   
        if has_article or has_law_name or legal_count >= 2:
            return QueryType.LEGAL
        
        if product_count >= 1 and has_dispute_type:
            return QueryType.PRODUCT_SPECIFIC
        
        if practical_count >= 2 or '' in query_lower:
            return QueryType.PRACTICAL
        
        return QueryType.GENERAL
    
    def _extract_law_articles(self, query: str) -> List[Dict]:
        """
          
        
        :
        - "123" -> {law_name: None, article_no: "123"}
        - " 750" -> {law_name: "", article_no: "750"}
        - "10 2" -> {law_name: None, article_no: "10", paragraph_no: "2"}
        """
        articles = []
        
        #  1: " N"
        pattern1 = r'([-\s]+[]?)\s*(\s*\d+\s*)'
        matches1 = re.findall(pattern1, query)
        for law_name, article_no in matches1:
            law_name = law_name.strip()
            article_no = re.sub(r'\s+', '', article_no)
            articles.append({
                'law_name': law_name,
                'article_no': article_no,
                'paragraph_no': None
            })
        
        #  2: "N M"
        pattern2 = r'(\s*\d+\s*)\s*(\s*\d+\s*)?'
        matches2 = re.findall(pattern2, query)
        for article_no, paragraph_no in matches2:
            article_no = re.sub(r'\s+', '', article_no)
            paragraph_no = re.sub(r'\s+', '', paragraph_no) if paragraph_no else None
            
            #    
            if not any(a['article_no'] == article_no for a in articles):
                articles.append({
                    'law_name': None,
                    'article_no': article_no,
                    'paragraph_no': paragraph_no
                })
        
        return articles
    
    def _extract_product_names(self, query: str, query_lower: str) -> List[str]:
        """
          ( - Phase 2)
        
        :
        1.     (PRODUCT_KEYWORDS)
        2.     ("", "" )
        3.   (PRODUCT_SYNONYMS)
        4.    ("~/ ", "~/ " )
        """
        items = set()
        
        # 1.     ( )
        for product in self.PRODUCT_KEYWORDS:
            product_lower = product.lower()
            #     (  )
            if product_lower in query_lower:
                # ""   
                idx = query_lower.find(product_lower)
                #   
                before_ok = (idx == 0 or not query_lower[idx-1].isalnum())
                after_ok = (idx + len(product_lower) >= len(query_lower) or 
                           not query_lower[idx + len(product_lower)].isalnum())
                
                if before_ok and after_ok:
                    items.add(product)
        
        # 2.     ( )
        # "", "", "", "TV" 
        for product in self.PRODUCT_KEYWORDS:
            patterns = [
                rf'{product}(?:||||||||||||)',
                rf'{product}(?:|)\s',
                rf'{product}\s*(?:||||||)',
            ]
            for pattern in patterns:
                if re.search(pattern, query):
                    items.add(product)
                    break
        
        # 3.   
        for synonym, standard in self.PRODUCT_SYNONYMS.items():
            if synonym.lower() in query_lower:
                items.add(standard)
        
        # 4.    ( )
        context_patterns = [
            (r'([-a-zA-Z0-9]+)(?:|)\s*(?:||||)', 'purchase'),
            (r'([-a-zA-Z0-9]+)(?:|)\s*(?:||||)', 'defect'),
            (r'([-a-zA-Z0-9]+)(?:|)\s*(?:|||)', 'dispute'),
            (r'([-a-zA-Z0-9]+)\s*(?:||AS|)', 'warranty'),
        ]
        
        for pattern, category in context_patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                item = match.strip()
                #      
                if (2 <= len(item) <= 15 and 
                    item not in ['', '', '', '', '', '', '', '', '']):
                    # PRODUCT_KEYWORDS  
                    if item in self.PRODUCT_KEYWORDS or item in self.PRODUCT_SYNONYMS:
                        items.add(item)
        
        # 5.  
        # -   
        generic_terms = {'', '', '', '', '', '', '', '', '', ''}
        items = items - generic_terms
        
        #  5,   (    )
        return sorted(list(items), key=len)[:5]
    
    def _extract_keywords(self, query: str, query_lower: str) -> List[str]:
        """
          
        
        :
        1.   (  )
        2.   
        """
        keywords = set()
        
        #   ( )
        words = re.findall(r'[-a-zA-Z0-9]+', query)
        
        for word in words:
            if len(word) >= 2:
                keywords.add(word)
        
        #  15 
        return list(keywords)[:15]
    
    def _infer_dispute_types(self, query: str, query_lower: str) -> List[str]:
        """
          
        
             
        """
        dispute_types = []
        
        for dispute_type, keywords in self.DISPUTE_TYPE_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                dispute_types.append(dispute_type)
        
        return dispute_types
    
    def _extract_law_names(self, query: str) -> List[str]:
        """ """
        law_names = []
        
        for law_name in self.LAW_NAMES:
            if law_name in query:
                law_names.append(law_name)
        
        return law_names


#  
def analyze_query(query: str) -> QueryAnalysis:
    """   """
    analyzer = QueryAnalyzer()
    return analyzer.analyze(query)
