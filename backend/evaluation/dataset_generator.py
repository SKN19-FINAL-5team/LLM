"""
똑소리 프로젝트 - RAG 평가용 골드 데이터셋 생성 도구
작성일: 2026-01-05
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from rag.retriever import RAGRetriever
except ImportError:
    RAGRetriever = None  # 의존성 없이도 데이터셋 생성 가능


class GoldDatasetGenerator:
    """골드 데이터셋 생성 및 관리"""
    
    def __init__(self, retriever: Optional[RAGRetriever] = None):
        self.retriever = retriever
        self.dataset = []
        self.query_id_counter = 1
    
    def add_query(
        self,
        query: str,
        query_type: str,
        expected_doc_types: List[str],
        relevant_chunk_ids: List[str],
        highly_relevant_chunk_ids: Optional[List[str]] = None,
        irrelevant_chunk_ids: Optional[List[str]] = None,
        difficulty: str = "medium",
        category: Optional[str] = None,
        annotator: str = "manual"
    ) -> Dict:
        """
        골드 데이터셋에 질문 추가
        
        Args:
            query: 사용자 질문
            query_type: 질문 유형 (general_inquiry, legal_interpretation, similar_case)
            expected_doc_types: 기대되는 문서 유형 목록
            relevant_chunk_ids: 관련 있는 청크 ID 목록
            highly_relevant_chunk_ids: 매우 관련 있는 청크 ID 목록
            irrelevant_chunk_ids: 관련 없는 청크 ID 목록
            difficulty: 난이도 (easy, medium, hard)
            category: 카테고리
            annotator: 작성자
        
        Returns:
            추가된 질문 항목
        """
        query_id = f"Q{self.query_id_counter:03d}"
        self.query_id_counter += 1
        
        item = {
            "query_id": query_id,
            "query": query,
            "query_type": query_type,
            "expected_doc_types": expected_doc_types,
            "relevant_chunk_ids": relevant_chunk_ids,
            "highly_relevant_chunk_ids": highly_relevant_chunk_ids or [],
            "irrelevant_chunk_ids": irrelevant_chunk_ids or [],
            "metadata": {
                "difficulty": difficulty,
                "category": category,
                "created_at": datetime.now().isoformat(),
                "annotator": annotator
            }
        }
        
        self.dataset.append(item)
        return item
    
    def suggest_relevant_chunks(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        현재 RAG 시스템을 사용하여 관련 청크 추천
        
        Args:
            query: 질문
            top_k: 추천할 청크 수
        
        Returns:
            추천된 청크 목록
        """
        if not self.retriever:
            raise ValueError("Retriever가 설정되지 않았습니다.")
        
        results = self.retriever.hybrid_search(query, top_k=top_k)
        
        suggestions = []
        for result in results:
            suggestions.append({
                "chunk_id": result.chunk_id,
                "doc_type": result.doc_type,
                "doc_title": result.doc_title,
                "chunk_type": result.chunk_type,
                "similarity": result.similarity,
                "content_preview": result.content[:200] + "..."
            })
        
        return suggestions
    
    def save_dataset(self, filepath: str, pretty: bool = True):
        """
        데이터셋을 JSON 파일로 저장
        
        Args:
            filepath: 저장할 파일 경로
            pretty: 보기 좋게 포맷팅 여부
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(self.dataset, f, ensure_ascii=False, indent=2)
            else:
                json.dump(self.dataset, f, ensure_ascii=False)
        
        print(f"✅ 데이터셋 저장 완료: {filepath}")
        print(f"   총 {len(self.dataset)}개 질문")
    
    def load_dataset(self, filepath: str):
        """
        JSON 파일에서 데이터셋 로드
        
        Args:
            filepath: 로드할 파일 경로
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            self.dataset = json.load(f)
        
        # query_id_counter 업데이트
        if self.dataset:
            max_id = max(int(item['query_id'][1:]) for item in self.dataset)
            self.query_id_counter = max_id + 1
        
        print(f"✅ 데이터셋 로드 완료: {filepath}")
        print(f"   총 {len(self.dataset)}개 질문")
    
    def get_statistics(self) -> Dict:
        """데이터셋 통계 반환"""
        if not self.dataset:
            return {}
        
        stats = {
            "total_queries": len(self.dataset),
            "by_query_type": {},
            "by_difficulty": {},
            "by_category": {},
            "avg_relevant_chunks": 0,
            "avg_highly_relevant_chunks": 0
        }
        
        total_relevant = 0
        total_highly_relevant = 0
        
        for item in self.dataset:
            # 질문 유형별
            qtype = item['query_type']
            stats['by_query_type'][qtype] = stats['by_query_type'].get(qtype, 0) + 1
            
            # 난이도별
            difficulty = item['metadata']['difficulty']
            stats['by_difficulty'][difficulty] = stats['by_difficulty'].get(difficulty, 0) + 1
            
            # 카테고리별
            category = item['metadata'].get('category')
            if category:
                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            # 평균 청크 수
            total_relevant += len(item['relevant_chunk_ids'])
            total_highly_relevant += len(item['highly_relevant_chunk_ids'])
        
        stats['avg_relevant_chunks'] = total_relevant / len(self.dataset)
        stats['avg_highly_relevant_chunks'] = total_highly_relevant / len(self.dataset)
        
        return stats
    
    def print_statistics(self):
        """데이터셋 통계 출력"""
        stats = self.get_statistics()
        
        if not stats:
            print("데이터셋이 비어있습니다.")
            return
        
        print("\n" + "=" * 60)
        print("골드 데이터셋 통계")
        print("=" * 60)
        print(f"총 질문 수: {stats['total_queries']}개")
        print()
        
        print("질문 유형별 분포:")
        for qtype, count in stats['by_query_type'].items():
            percentage = (count / stats['total_queries']) * 100
            print(f"  - {qtype}: {count}개 ({percentage:.1f}%)")
        print()
        
        print("난이도별 분포:")
        for difficulty, count in stats['by_difficulty'].items():
            percentage = (count / stats['total_queries']) * 100
            print(f"  - {difficulty}: {count}개 ({percentage:.1f}%)")
        print()
        
        if stats['by_category']:
            print("카테고리별 분포:")
            for category, count in stats['by_category'].items():
                percentage = (count / stats['total_queries']) * 100
                print(f"  - {category}: {count}개 ({percentage:.1f}%)")
            print()
        
        print(f"평균 관련 청크 수: {stats['avg_relevant_chunks']:.1f}개")
        print(f"평균 매우 관련 있는 청크 수: {stats['avg_highly_relevant_chunks']:.1f}개")
        print("=" * 60)


def create_initial_dataset():
    """초기 골드 데이터셋 생성 (30개 질문)"""
    generator = GoldDatasetGenerator()
    
    # 1. 일반 문의 (general_inquiry) - 15개
    
    generator.add_query(
        query="온라인으로 구매한 제품이 불량이에요. 환불 받을 수 있나요?",
        query_type="general_inquiry",
        expected_doc_types=["counsel_case", "law"],
        relevant_chunk_ids=[
            "consumer.go.kr:consumer_counsel_case:53321::chunk0"
        ],
        highly_relevant_chunk_ids=[
            "consumer.go.kr:consumer_counsel_case:53321::chunk0"
        ],
        difficulty="easy",
        category="환불",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="가전제품 감가상각은 어떻게 계산하나요?",
        query_type="general_inquiry",
        expected_doc_types=["counsel_case"],
        relevant_chunk_ids=[
            "consumer.go.kr:consumer_counsel_case:53321::chunk0"
        ],
        highly_relevant_chunk_ids=[
            "consumer.go.kr:consumer_counsel_case:53321::chunk0"
        ],
        difficulty="medium",
        category="감가상각",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="휴대폰 액정이 자연 파손되었는데 무상 수리가 가능한가요?",
        query_type="general_inquiry",
        expected_doc_types=["counsel_case", "mediation_case"],
        relevant_chunk_ids=[],
        difficulty="medium",
        category="제품하자",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="배송 중 제품이 파손되었어요. 누구에게 책임을 물어야 하나요?",
        query_type="general_inquiry",
        expected_doc_types=["counsel_case", "law"],
        relevant_chunk_ids=[],
        difficulty="medium",
        category="배송",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="청약철회는 언제까지 가능한가요?",
        query_type="general_inquiry",
        expected_doc_types=["law", "counsel_case"],
        relevant_chunk_ids=[],
        difficulty="easy",
        category="청약철회",
        annotator="expert_1"
    )
    
    # 2. 법률 해석 (legal_interpretation) - 8개
    
    generator.add_query(
        query="소비자기본법에서 소비자의 권리는 무엇인가요?",
        query_type="legal_interpretation",
        expected_doc_types=["law"],
        relevant_chunk_ids=[],
        difficulty="easy",
        category="소비자권리",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="전자상거래법에서 청약철회 기간은 어떻게 규정되어 있나요?",
        query_type="legal_interpretation",
        expected_doc_types=["law"],
        relevant_chunk_ids=[],
        difficulty="medium",
        category="청약철회",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="제조물책임법에서 제조업자의 책임 범위는?",
        query_type="legal_interpretation",
        expected_doc_types=["law"],
        relevant_chunk_ids=[],
        difficulty="hard",
        category="제조물책임",
        annotator="expert_1"
    )
    
    # 3. 유사 사례 검색 (similar_case) - 7개
    
    generator.add_query(
        query="아파트 누수로 인한 손해배상 사례가 있나요?",
        query_type="similar_case",
        expected_doc_types=["mediation_case"],
        relevant_chunk_ids=[
            "consumer.go.kr:consumer_mediation_case:12448::chunk0"
        ],
        highly_relevant_chunk_ids=[
            "consumer.go.kr:consumer_mediation_case:12448::chunk0"
        ],
        difficulty="medium",
        category="주거시설",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="에어컨 설치 불량으로 누수가 발생한 사례를 찾고 있어요.",
        query_type="similar_case",
        expected_doc_types=["mediation_case"],
        relevant_chunk_ids=[
            "consumer.go.kr:consumer_mediation_case:12448::chunk0"
        ],
        highly_relevant_chunk_ids=[
            "consumer.go.kr:consumer_mediation_case:12448::chunk0"
        ],
        difficulty="easy",
        category="주거시설",
        annotator="expert_1"
    )
    
    print(f"✅ 초기 데이터셋 생성 완료: {len(generator.dataset)}개 질문")
    return generator


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("골드 데이터셋 생성 도구")
    print("=" * 60)
    print()
    print("1. 초기 데이터셋 생성 (샘플 10개)")
    print("2. 기존 데이터셋 로드 및 편집")
    print("3. 종료")
    print()
    
    choice = input("선택 (1-3): ").strip()
    
    if choice == '1':
        generator = create_initial_dataset()
        generator.print_statistics()
        
        # 저장
        output_dir = Path(__file__).parent / "datasets"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "gold_v1.json"
        
        generator.save_dataset(str(output_path))
        print(f"\n저장 위치: {output_path}")
    
    elif choice == '2':
        print("기존 데이터셋 로드 기능은 추후 구현 예정입니다.")
    
    elif choice == '3':
        print("종료합니다.")
    
    else:
        print("잘못된 선택입니다.")


if __name__ == "__main__":
    main()
