"""
Agency Recommender Module
        
"""

from typing import List, Dict, Tuple
from collections import Counter


class AgencyRecommender:
    """   (  +   )"""
    
    #  
    AGENCIES = {
        'kca': {
            'name': '',
            'full_name': ' (Korea Consumer Agency)',
            'description': '    (, , ,  )'
        },
        'ecmc': {
            'name': '',
            'full_name': ' (Electronic Commerce Mediation Committee)',
            'description': '     '
        },
        'kcdrc': {
            'name': '',
            'full_name': ' (Korea Copyright Commission)',
            'description': '     '
        }
    }
    
    #    ( )
    KEYWORD_RULES = {
        'ecmc': [
            #  
            '', '', '', '', '',
            '', '', '', '', '',
            '', '', '',
            # 
            '', '', '11', 'G', '',
            '', '', '',
            # /
            '', '', '', '',
            '', '', ''
        ],
        'kcdrc': [
            #  
            '', '', '', '', '',
            '', '', '', '',
            # 
            '', '', '', '', '',
            '', '', '', '', '',
            #  
            '', '', '', '',
            '', '', '', ''
        ],
        'kca': [
            #  
            '', '', '', '', '',
            '', '', '', '', '',
            '', '', '',
            # 
            '', '', '', '', '',
            '', '', '', '',
            #  
            '', '', '', '', 'A/S',
            '', ''
        ]
    }
    
    def __init__(self, rule_weight: float = 0.7, stat_weight: float = 0.3):
        """
        Args:
            rule_weight:    (: 0.7)
            stat_weight:     (: 0.3)
        """
        self.rule_weight = rule_weight
        self.stat_weight = stat_weight
    
    def calculate_rule_scores(self, query: str) -> Dict[str, float]:
        """
            ( )
        
        Args:
            query:  
            
        Returns:
               (0~1 )
        """
        query_lower = query.lower()
        scores = {'kca': 0.0, 'ecmc': 0.0, 'kcdrc': 0.0}
        
        #    
        for agency, keywords in self.KEYWORD_RULES.items():
            match_count = 0
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    match_count += 1
            
            #   (   )
            if match_count > 0:
                #      (  )
                import math
                scores[agency] = math.log1p(match_count) / math.log1p(len(keywords))
        
        # KCA    (   0  )
        if all(score == 0 for score in scores.values()):
            scores['kca'] = 0.3  #  
        
        #  (0~1 )
        max_score = max(scores.values())
        if max_score > 0:
            scores = {k: v / max_score for k, v in scores.items()}
        
        return scores
    
    def calculate_stat_scores(self, search_results: List[Dict]) -> Dict[str, float]:
        """
             
        
        Args:
            search_results:   
            
        Returns:
               (0~1 )
        """
        if not search_results:
            return {'kca': 0.0, 'ecmc': 0.0, 'kcdrc': 0.0}
        
        #      
        agency_scores = {'kca': 0.0, 'ecmc': 0.0, 'kcdrc': 0.0}
        
        for idx, chunk in enumerate(search_results):
            agency = chunk.get('agency', '').lower()
            if agency in agency_scores:
                #    (   )
                rank_weight = 1.0 / (idx + 1)
                
                #  
                similarity = chunk.get('similarity', 0.0)
                
                #   =   * 
                agency_scores[agency] += rank_weight * similarity
        
        #  (0~1 )
        total = sum(agency_scores.values())
        if total > 0:
            agency_scores = {k: v / total for k, v in agency_scores.items()}
        
        return agency_scores
    
    def recommend(
        self, 
        query: str, 
        search_results: List[Dict] = None,
        top_n: int = 2
    ) -> List[Tuple[str, float, Dict]]:
        """
          ( +  )
        
        Args:
            query:  
            search_results:    ()
            top_n:     (: 2)
            
        Returns:
            [(, , ), ...]   ( )
        """
        #   
        rule_scores = self.calculate_rule_scores(query)
        
        #    
        stat_scores = {'kca': 0.0, 'ecmc': 0.0, 'kcdrc': 0.0}
        if search_results:
            stat_scores = self.calculate_stat_scores(search_results)
        
        #    ( )
        final_scores = {}
        for agency in ['kca', 'ecmc', 'kcdrc']:
            final_scores[agency] = (
                self.rule_weight * rule_scores[agency] +
                self.stat_weight * stat_scores[agency]
            )
        
        #   
        sorted_agencies = sorted(
            final_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        #  N  (  DB )
        recommendations = []
        for agency_code, score in sorted_agencies[:top_n]:
            agency_info = self.AGENCIES[agency_code].copy()
            agency_info['rule_score'] = rule_scores[agency_code]
            agency_info['stat_score'] = stat_scores[agency_code]
            # DB source_org  (KCA, ECMC)  
            recommendations.append((agency_code.upper(), score, agency_info))
        
        return recommendations
    
    def explain_recommendation(
        self, 
        query: str, 
        search_results: List[Dict] = None
    ) -> Dict:
        """
             
        
        Args:
            query:  
            search_results:   
            
        Returns:
                  
        """
        recommendations = self.recommend(query, search_results, top_n=3)
        
        #   
        agency_distribution = {}
        if search_results:
            agency_counts = Counter(
                chunk.get('agency', 'unknown') 
                for chunk in search_results
            )
            agency_distribution = dict(agency_counts)
        
        return {
            'recommendations': [
                {
                    'agency_code': code,
                    'agency_name': info['name'],
                    'full_name': info['full_name'],
                    'description': info['description'],
                    'final_score': score,
                    'rule_score': info['rule_score'],
                    'stat_score': info['stat_score'],
                    'rank': idx + 1
                }
                for idx, (code, score, info) in enumerate(recommendations)
            ],
            'search_results_distribution': agency_distribution,
            'weights': {
                'rule_weight': self.rule_weight,
                'stat_weight': self.stat_weight
            }
        }
    
    def get_agency_info(self, agency_code: str) -> Dict:
        """
           
        
        Args:
            agency_code:   ('kca', 'ecmc', 'kcdrc')
            
        Returns:
              
        """
        return self.AGENCIES.get(agency_code.lower(), {})
    
    def format_recommendation_text(
        self, 
        query: str, 
        search_results: List[Dict] = None
    ) -> str:
        """
             
        
        Args:
            query:  
            search_results:   
            
        Returns:
              
        """
        explanation = self.explain_recommendation(query, search_results)
        recommendations = explanation['recommendations']
        
        if not recommendations:
            return "    ."
        
        # 1 
        primary = recommendations[0]
        text_parts = [
            f"  : {primary['agency_name']}",
            f"   {primary['description']}",
            f"   ( : {primary['final_score']:.2f})",
            ""
        ]
        
        # 2  ( )
        if len(recommendations) > 1:
            secondary = recommendations[1]
            text_parts.extend([
                f"  : {secondary['agency_name']}",
                f"   {secondary['description']}",
                f"   ( : {secondary['final_score']:.2f})",
                ""
            ])
        
        #    ( )
        if explanation['search_results_distribution']:
            text_parts.append("   :")
            for agency, count in explanation['search_results_distribution'].items():
                agency_name = self.AGENCIES.get(agency, {}).get('name', agency)
                text_parts.append(f"   - {agency_name}: {count}")
        
        return "\n".join(text_parts)


#  
def recommend_agency(
    query: str, 
    search_results: List[Dict] = None,
    top_n: int = 2
) -> List[Tuple[str, float, Dict]]:
    """
       
    
    Args:
        query:  
        search_results:   
        top_n:    
        
    Returns:
          
    """
    recommender = AgencyRecommender()
    return recommender.recommend(query, search_results, top_n)


def explain_agency_recommendation(
    query: str, 
    search_results: List[Dict] = None
) -> Dict:
    """
        
    
    Args:
        query:  
        search_results:   
        
    Returns:
            
    """
    recommender = AgencyRecommender()
    return recommender.explain_recommendation(query, search_results)
