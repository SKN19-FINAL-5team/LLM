"""
Golden Set Loader Module
Golden set 데이터를 로드하고 선택하는 모듈
"""

import json
from pathlib import Path
from typing import List, Dict, Optional


class GoldenSetLoader:
    """Golden set 데이터를 로드하고 관리하는 클래스"""
    
    def __init__(self, golden_set_path: Optional[Path] = None):
        """
        Args:
            golden_set_path: Golden set JSON 파일 경로
                            None이면 기본 경로 사용
        """
        if golden_set_path is None:
            # 기본 경로: backend/evaluation/datasets/gold_real_consumer_cases.json
            backend_dir = Path(__file__).parent.parent.parent
            golden_set_path = backend_dir / 'evaluation' / 'datasets' / 'gold_real_consumer_cases.json'
        
        self.golden_set_path = Path(golden_set_path)
        self.data = None
        self.test_cases = []
    
    def load(self) -> bool:
        """
        Golden set 파일 로드
        
        Returns:
            로드 성공 여부
        """
        try:
            if not self.golden_set_path.exists():
                print(f"❌ Golden set 파일을 찾을 수 없습니다: {self.golden_set_path}")
                return False
            
            with open(self.golden_set_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            self.test_cases = self.data.get('test_cases', [])
            
            print(f"✅ Golden set 로드 완료: {len(self.test_cases)}개 쿼리")
            return True
            
        except Exception as e:
            print(f"❌ Golden set 로드 실패: {e}")
            return False
    
    def get_all_queries(self) -> List[Dict]:
        """
        모든 쿼리 반환
        
        Returns:
            쿼리 리스트
        """
        if not self.test_cases:
            if not self.load():
                return []
        
        return self.test_cases
    
    def get_query_by_id(self, query_id: str) -> Optional[Dict]:
        """
        ID로 쿼리 조회
        
        Args:
            query_id: 쿼리 ID (예: "Q001")
        
        Returns:
            쿼리 딕셔너리 또는 None
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
        인덱스로 쿼리 조회
        
        Args:
            index: 인덱스 (0부터 시작)
        
        Returns:
            쿼리 딕셔너리 또는 None
        """
        if not self.test_cases:
            if not self.load():
                return None
        
        if 0 <= index < len(self.test_cases):
            return self.test_cases[index]
        
        return None
    
    def display_queries(self, limit: Optional[int] = None):
        """
        쿼리 목록 표시
        
        Args:
            limit: 표시할 최대 개수 (None이면 모두 표시)
        """
        if not self.test_cases:
            if not self.load():
                return
        
        queries_to_display = self.test_cases[:limit] if limit else self.test_cases
        
        print("\n" + "=" * 80)
        print("Golden Set 쿼리 목록")
        print("=" * 80)
        
        for idx, test_case in enumerate(queries_to_display, 1):
            query_id = test_case.get('query_id', f'N/A-{idx}')
            query = test_case.get('query', '')
            query_type = test_case.get('query_type', 'N/A')
            difficulty = test_case.get('difficulty', 'N/A')
            
            print(f"\n[{idx}] {query_id}")
            print(f"    질문: {query}")
            print(f"    유형: {query_type}, 난이도: {difficulty}")
        
        print("\n" + "=" * 80)
        print(f"총 {len(self.test_cases)}개 쿼리")
        if limit and limit < len(self.test_cases):
            print(f"(상위 {limit}개만 표시)")
        print("=" * 80)
    
    def select_query_interactive(self) -> Optional[Dict]:
        """
        대화형으로 쿼리 선택
        
        Returns:
            선택된 쿼리 딕셔너리 또는 None
        """
        if not self.test_cases:
            if not self.load():
                return None
        
        self.display_queries(limit=20)  # 상위 20개만 표시
        
        print("\n쿼리를 선택하세요:")
        print("  - 번호 입력: 해당 쿼리 선택")
        print("  - 'all' 입력: 모든 쿼리 반환 (배치 모드)")
        print("  - 'q' 또는 'quit' 입력: 취소")
        
        try:
            user_input = input("\n선택: ").strip()
            
            if user_input.lower() in ['q', 'quit', 'exit']:
                return None
            
            if user_input.lower() == 'all':
                return {'all': True, 'queries': self.test_cases}
            
            # 번호로 선택
            index = int(user_input) - 1
            if 0 <= index < len(self.test_cases):
                return self.test_cases[index]
            else:
                print(f"❌ 잘못된 번호입니다. 1-{len(self.test_cases)} 사이의 숫자를 입력하세요.")
                return None
                
        except ValueError:
            print("❌ 숫자를 입력하세요.")
            return None
        except KeyboardInterrupt:
            print("\n취소되었습니다.")
            return None
    
    def get_dataset_info(self) -> Dict:
        """
        데이터셋 정보 반환
        
        Returns:
            데이터셋 정보 딕셔너리
        """
        if not self.data:
            if not self.load():
                return {}
        
        return self.data.get('dataset_info', {})


if __name__ == "__main__":
    # 테스트
    loader = GoldenSetLoader()
    
    if loader.load():
        print("\n=== 데이터셋 정보 ===")
        info = loader.get_dataset_info()
        for key, value in info.items():
            print(f"{key}: {value}")
        
        print("\n=== 첫 번째 쿼리 ===")
        first_query = loader.get_query_by_index(0)
        if first_query:
            print(f"ID: {first_query.get('query_id')}")
            print(f"Query: {first_query.get('query')}")
        
        print("\n=== 쿼리 목록 표시 ===")
        loader.display_queries(limit=5)
