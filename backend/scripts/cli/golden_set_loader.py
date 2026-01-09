"""
Golden Set Loader Module
Golden set    
"""

import json
from pathlib import Path
from typing import List, Dict, Optional


class GoldenSetLoader:
    """Golden set    """
    
    def __init__(self, golden_set_path: Optional[Path] = None):
        """
        Args:
            golden_set_path: Golden set JSON  
                            None   
        """
        if golden_set_path is None:
            #  : backend/evaluation/datasets/gold_real_consumer_cases.json
            backend_dir = Path(__file__).parent.parent.parent
            golden_set_path = backend_dir / 'evaluation' / 'datasets' / 'gold_real_consumer_cases.json'
        
        self.golden_set_path = Path(golden_set_path)
        self.data = None
        self.test_cases = []
    
    def load(self) -> bool:
        """
        Golden set  
        
        Returns:
              
        """
        try:
            if not self.golden_set_path.exists():
                print(f" Golden set    : {self.golden_set_path}")
                return False
            
            with open(self.golden_set_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            self.test_cases = self.data.get('test_cases', [])
            
            print(f" Golden set  : {len(self.test_cases)} ")
            return True
            
        except Exception as e:
            print(f" Golden set  : {e}")
            return False
    
    def get_all_queries(self) -> List[Dict]:
        """
          
        
        Returns:
             
        """
        if not self.test_cases:
            if not self.load():
                return []
        
        return self.test_cases
    
    def get_query_by_id(self, query_id: str) -> Optional[Dict]:
        """
        ID  
        
        Args:
            query_id:  ID (: "Q001")
        
        Returns:
               None
        """
        if not self.test_cases:
            if not self.load():
                return None
        
        for test_case in self.test_cases:
            if test_case.get('query_id') == query_id:
                return test_case
        
        return None
    
    def get_query_by_index(self, index: int) -> Optional[Dict]:
        """
          
        
        Args:
            index:  (0 )
        
        Returns:
               None
        """
        if not self.test_cases:
            if not self.load():
                return None
        
        if 0 <= index < len(self.test_cases):
            return self.test_cases[index]
        
        return None
    
    def display_queries(self, limit: Optional[int] = None):
        """
          
        
        Args:
            limit:    (None  )
        """
        if not self.test_cases:
            if not self.load():
                return
        
        queries_to_display = self.test_cases[:limit] if limit else self.test_cases
        
        print("\n" + "=" * 80)
        print("Golden Set  ")
        print("=" * 80)
        
        for idx, test_case in enumerate(queries_to_display, 1):
            query_id = test_case.get('query_id', f'N/A-{idx}')
            query = test_case.get('query', '')
            query_type = test_case.get('query_type', 'N/A')
            difficulty = test_case.get('difficulty', 'N/A')
            
            print(f"\n[{idx}] {query_id}")
            print(f"    : {query}")
            print(f"    : {query_type}, : {difficulty}")
        
        print("\n" + "=" * 80)
        print(f" {len(self.test_cases)} ")
        if limit and limit < len(self.test_cases):
            print(f"( {limit} )")
        print("=" * 80)
    
    def select_query_interactive(self) -> Optional[Dict]:
        """
          
        
        Returns:
                None
        """
        if not self.test_cases:
            if not self.load():
                return None
        
        self.display_queries(limit=20)  #  20 
        
        print("\n :")
        print("  -  :   ")
        print("  - 'all' :    ( )")
        print("  - 'q'  'quit' : ")
        
        try:
            user_input = input("\n: ").strip()
            
            if user_input.lower() in ['q', 'quit', 'exit']:
                return None
            
            if user_input.lower() == 'all':
                return {'all': True, 'queries': self.test_cases}
            
            #  
            index = int(user_input) - 1
            if 0 <= index < len(self.test_cases):
                return self.test_cases[index]
            else:
                print(f"  . 1-{len(self.test_cases)}   .")
                return None
                
        except ValueError:
            print("  .")
            return None
        except KeyboardInterrupt:
            print("\n.")
            return None
    
    def get_dataset_info(self) -> Dict:
        """
          
        
        Returns:
              
        """
        if not self.data:
            if not self.load():
                return {}
        
        return self.data.get('dataset_info', {})


if __name__ == "__main__":
    # 
    loader = GoldenSetLoader()
    
    if loader.load():
        print("\n===   ===")
        info = loader.get_dataset_info()
        for key, value in info.items():
            print(f"{key}: {value}")
        
        print("\n===    ===")
        first_query = loader.get_query_by_index(0)
        if first_query:
            print(f"ID: {first_query.get('query_id')}")
            print(f"Query: {first_query.get('query')}")
        
        print("\n===    ===")
        loader.display_queries(limit=5)
