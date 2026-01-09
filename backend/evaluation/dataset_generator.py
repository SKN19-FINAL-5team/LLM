"""
  - RAG     
: 2026-01-05
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

#    
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from rag.retriever import RAGRetriever
except ImportError:
    RAGRetriever = None  #     


class GoldDatasetGenerator:
    """    """
    
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
           
        
        Args:
            query:  
            query_type:   (general_inquiry, legal_interpretation, similar_case)
            expected_doc_types:    
            relevant_chunk_ids:    ID 
            highly_relevant_chunk_ids:     ID 
            irrelevant_chunk_ids:    ID 
            difficulty:  (easy, medium, hard)
            category: 
            annotator: 
        
        Returns:
              
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
         RAG     
        
        Args:
            query: 
            top_k:   
        
        Returns:
              
        """
        if not self.retriever:
            raise ValueError("Retriever  .")
        
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
         JSON  
        
        Args:
            filepath:   
            pretty:    
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(self.dataset, f, ensure_ascii=False, indent=2)
            else:
                json.dump(self.dataset, f, ensure_ascii=False)
        
        print(f"   : {filepath}")
        print(f"    {len(self.dataset)} ")
    
    def load_dataset(self, filepath: str):
        """
        JSON   
        
        Args:
            filepath:   
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            self.dataset = json.load(f)
        
        # query_id_counter 
        if self.dataset:
            max_id = max(int(item['query_id'][1:]) for item in self.dataset)
            self.query_id_counter = max_id + 1
        
        print(f"   : {filepath}")
        print(f"    {len(self.dataset)} ")
    
    def get_statistics(self) -> Dict:
        """  """
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
            #  
            qtype = item['query_type']
            stats['by_query_type'][qtype] = stats['by_query_type'].get(qtype, 0) + 1
            
            # 
            difficulty = item['metadata']['difficulty']
            stats['by_difficulty'][difficulty] = stats['by_difficulty'].get(difficulty, 0) + 1
            
            # 
            category = item['metadata'].get('category')
            if category:
                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            #   
            total_relevant += len(item['relevant_chunk_ids'])
            total_highly_relevant += len(item['highly_relevant_chunk_ids'])
        
        stats['avg_relevant_chunks'] = total_relevant / len(self.dataset)
        stats['avg_highly_relevant_chunks'] = total_highly_relevant / len(self.dataset)
        
        return stats
    
    def print_statistics(self):
        """  """
        stats = self.get_statistics()
        
        if not stats:
            print(" .")
            return
        
        print("\n" + "=" * 60)
        print("  ")
        print("=" * 60)
        print(f"  : {stats['total_queries']}")
        print()
        
        print("  :")
        for qtype, count in stats['by_query_type'].items():
            percentage = (count / stats['total_queries']) * 100
            print(f"  - {qtype}: {count} ({percentage:.1f}%)")
        print()
        
        print(" :")
        for difficulty, count in stats['by_difficulty'].items():
            percentage = (count / stats['total_queries']) * 100
            print(f"  - {difficulty}: {count} ({percentage:.1f}%)")
        print()
        
        if stats['by_category']:
            print(" :")
            for category, count in stats['by_category'].items():
                percentage = (count / stats['total_queries']) * 100
                print(f"  - {category}: {count} ({percentage:.1f}%)")
            print()
        
        print(f"   : {stats['avg_relevant_chunks']:.1f}")
        print(f"     : {stats['avg_highly_relevant_chunks']:.1f}")
        print("=" * 60)


def create_initial_dataset():
    """    (30 )"""
    generator = GoldDatasetGenerator()
    
    # 1.   (general_inquiry) - 15
    
    generator.add_query(
        query="   .    ?",
        query_type="general_inquiry",
        expected_doc_types=["counsel_case", "law"],
        relevant_chunk_ids=[
            "consumer.go.kr:consumer_counsel_case:53321::chunk0"
        ],
        highly_relevant_chunk_ids=[
            "consumer.go.kr:consumer_counsel_case:53321::chunk0"
        ],
        difficulty="easy",
        category="",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="   ?",
        query_type="general_inquiry",
        expected_doc_types=["counsel_case"],
        relevant_chunk_ids=[
            "consumer.go.kr:consumer_counsel_case:53321::chunk0"
        ],
        highly_relevant_chunk_ids=[
            "consumer.go.kr:consumer_counsel_case:53321::chunk0"
        ],
        difficulty="medium",
        category="",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="      ?",
        query_type="general_inquiry",
        expected_doc_types=["counsel_case", "mediation_case"],
        relevant_chunk_ids=[],
        difficulty="medium",
        category="",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="   .    ?",
        query_type="general_inquiry",
        expected_doc_types=["counsel_case", "law"],
        relevant_chunk_ids=[],
        difficulty="medium",
        category="",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="  ?",
        query_type="general_inquiry",
        expected_doc_types=["law", "counsel_case"],
        relevant_chunk_ids=[],
        difficulty="easy",
        category="",
        annotator="expert_1"
    )
    
    # 2.   (legal_interpretation) - 8
    
    generator.add_query(
        query="   ?",
        query_type="legal_interpretation",
        expected_doc_types=["law"],
        relevant_chunk_ids=[],
        difficulty="easy",
        category="",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="     ?",
        query_type="legal_interpretation",
        expected_doc_types=["law"],
        relevant_chunk_ids=[],
        difficulty="medium",
        category="",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="   ?",
        query_type="legal_interpretation",
        expected_doc_types=["law"],
        relevant_chunk_ids=[],
        difficulty="hard",
        category="",
        annotator="expert_1"
    )
    
    # 3.    (similar_case) - 7
    
    generator.add_query(
        query="     ?",
        query_type="similar_case",
        expected_doc_types=["mediation_case"],
        relevant_chunk_ids=[
            "consumer.go.kr:consumer_mediation_case:12448::chunk0"
        ],
        highly_relevant_chunk_ids=[
            "consumer.go.kr:consumer_mediation_case:12448::chunk0"
        ],
        difficulty="medium",
        category="",
        annotator="expert_1"
    )
    
    generator.add_query(
        query="       .",
        query_type="similar_case",
        expected_doc_types=["mediation_case"],
        relevant_chunk_ids=[
            "consumer.go.kr:consumer_mediation_case:12448::chunk0"
        ],
        highly_relevant_chunk_ids=[
            "consumer.go.kr:consumer_mediation_case:12448::chunk0"
        ],
        difficulty="easy",
        category="",
        annotator="expert_1"
    )
    
    print(f"    : {len(generator.dataset)} ")
    return generator


def main():
    """  """
    print("=" * 60)
    print("   ")
    print("=" * 60)
    print()
    print("1.    ( 10)")
    print("2.     ")
    print("3. ")
    print()
    
    choice = input(" (1-3): ").strip()
    
    if choice == '1':
        generator = create_initial_dataset()
        generator.print_statistics()
        
        # 
        output_dir = Path(__file__).parent / "datasets"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "gold_v1.json"
        
        generator.save_dataset(str(output_path))
        print(f"\n : {output_path}")
    
    elif choice == '2':
        print("      .")
    
    elif choice == '3':
        print(".")
    
    else:
        print(" .")


if __name__ == "__main__":
    main()
