"""
똑소리 프로젝트 - RAG 평가 실행 시스템
작성일: 2026-01-05
"""

import json
import time
from typing import List, Dict, Optional
from pathlib import Path
import sys

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.retriever import RAGRetriever
from evaluation.metrics import calculate_all_metrics


class RAGEvaluator:
    """RAG 시스템 평가 실행"""
    
    def __init__(self, retriever: RAGRetriever, dataset_path: str):
        """
        Args:
            retriever: RAG Retriever 인스턴스
            dataset_path: 골드 데이터셋 경로
        """
        self.retriever = retriever
        self.dataset_path = dataset_path
        self.dataset = []
        self.results = []
    
    def load_dataset(self):
        """골드 데이터셋 로드"""
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            self.dataset = json.load(f)
        print(f"✅ 데이터셋 로드 완료: {len(self.dataset)}개 질문")
    
    def evaluate_single_query(
        self,
        query_item: Dict,
        search_method: str = "hybrid",
        top_k: int = 10
    ) -> Dict:
        """
        단일 질문 평가
        
        Args:
            query_item: 질문 항목 (골드 데이터셋의 한 항목)
            search_method: 검색 방법 (vector, hybrid, multi_source)
            top_k: 검색할 청크 수
        
        Returns:
            평가 결과 딕셔너리
        """
        query = query_item['query']
        query_type = query_item['query_type']
        
        # 검색 실행
        start_time = time.time()
        
        if search_method == "vector":
            results = self.retriever.vector_search(query, top_k=top_k)
        elif search_method == "hybrid":
            results = self.retriever.hybrid_search(query, top_k=top_k)
        elif search_method == "multi_source":
            results = self.retriever.multi_source_search(query, query_type=query_type, top_k=top_k)
        else:
            raise ValueError(f"지원하지 않는 검색 방법: {search_method}")
        
        query_time = time.time() - start_time
        
        # 검색 결과 추출
        retrieved_chunk_ids = [r.chunk_id for r in results]
        retrieved_doc_types = [r.doc_type for r in results]
        retrieved_sources = [r.metadata.get('source_org', 'unknown') for r in results]
        
        # 정답 데이터
        relevant_chunk_ids = set(query_item['relevant_chunk_ids'])
        highly_relevant_chunk_ids = set(query_item['highly_relevant_chunk_ids'])
        expected_doc_types = set(query_item['expected_doc_types'])
        
        # 평가 지표 계산
        metrics = calculate_all_metrics(
            retrieved=retrieved_chunk_ids,
            relevant=relevant_chunk_ids,
            highly_relevant=highly_relevant_chunk_ids,
            expected_doc_types=expected_doc_types,
            retrieved_doc_types=retrieved_doc_types,
            retrieved_sources=retrieved_sources,
            query_time=query_time
        )
        
        # 결과 구성
        result = {
            "query_id": query_item['query_id'],
            "query": query,
            "query_type": query_type,
            "search_method": search_method,
            "metrics": metrics,
            "retrieved_chunk_ids": retrieved_chunk_ids,
            "relevant_chunk_ids": list(relevant_chunk_ids),
            "highly_relevant_chunk_ids": list(highly_relevant_chunk_ids),
            "num_retrieved": len(retrieved_chunk_ids),
            "num_relevant": len(relevant_chunk_ids),
            "num_relevant_retrieved": len(set(retrieved_chunk_ids) & relevant_chunk_ids)
        }
        
        return result
    
    def evaluate_all(
        self,
        search_methods: List[str] = ["vector", "hybrid", "multi_source"],
        top_k: int = 10
    ) -> Dict:
        """
        전체 데이터셋 평가
        
        Args:
            search_methods: 평가할 검색 방법 목록
            top_k: 검색할 청크 수
        
        Returns:
            전체 평가 결과
        """
        if not self.dataset:
            self.load_dataset()
        
        all_results = {method: [] for method in search_methods}
        
        print(f"\n{'=' * 60}")
        print(f"RAG 시스템 평가 시작")
        print(f"{'=' * 60}")
        print(f"데이터셋: {self.dataset_path}")
        print(f"질문 수: {len(self.dataset)}개")
        print(f"검색 방법: {', '.join(search_methods)}")
        print(f"Top-K: {top_k}")
        print()
        
        for method in search_methods:
            print(f"\n[{method.upper()}] 평가 중...")
            
            for i, query_item in enumerate(self.dataset, 1):
                result = self.evaluate_single_query(query_item, method, top_k)
                all_results[method].append(result)
                
                # 진행 상황 출력
                if i % 10 == 0 or i == len(self.dataset):
                    print(f"  진행: {i}/{len(self.dataset)} ({i/len(self.dataset)*100:.1f}%)")
            
            print(f"✅ [{method.upper()}] 평가 완료")
        
        print(f"\n{'=' * 60}")
        print("평가 완료!")
        print(f"{'=' * 60}\n")
        
        return all_results
    
    def calculate_aggregate_metrics(self, results: List[Dict]) -> Dict:
        """
        집계 지표 계산 (평균)
        
        Args:
            results: 개별 질문 평가 결과 목록
        
        Returns:
            집계된 지표 딕셔너리
        """
        if not results:
            return {}
        
        # 모든 지표 키 추출
        metric_keys = results[0]['metrics'].keys()
        
        # 각 지표의 평균 계산
        aggregate = {}
        for key in metric_keys:
            values = [r['metrics'][key] for r in results]
            aggregate[key] = sum(values) / len(values)
        
        # 추가 통계
        aggregate['total_queries'] = len(results)
        aggregate['total_relevant'] = sum(r['num_relevant'] for r in results)
        aggregate['total_relevant_retrieved'] = sum(r['num_relevant_retrieved'] for r in results)
        
        return aggregate
    
    def calculate_metrics_by_query_type(self, results: List[Dict]) -> Dict:
        """
        질문 유형별 지표 계산
        
        Args:
            results: 개별 질문 평가 결과 목록
        
        Returns:
            질문 유형별 집계 지표
        """
        by_type = {}
        
        for result in results:
            qtype = result['query_type']
            if qtype not in by_type:
                by_type[qtype] = []
            by_type[qtype].append(result)
        
        # 각 유형별 집계
        aggregate_by_type = {}
        for qtype, type_results in by_type.items():
            aggregate_by_type[qtype] = self.calculate_aggregate_metrics(type_results)
        
        return aggregate_by_type
    
    def save_results(self, all_results: Dict, output_dir: str):
        """
        평가 결과 저장
        
        Args:
            all_results: 전체 평가 결과
            output_dir: 출력 디렉토리
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # JSON 형식으로 저장
        json_path = output_path / f"evaluation_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 평가 결과 저장: {json_path}")
        
        # 요약 통계 저장
        summary = {}
        for method, results in all_results.items():
            summary[method] = {
                "aggregate": self.calculate_aggregate_metrics(results),
                "by_query_type": self.calculate_metrics_by_query_type(results)
            }
        
        summary_path = output_path / f"evaluation_summary_{timestamp}.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 요약 통계 저장: {summary_path}")
        
        return json_path, summary_path
    
    def print_summary(self, all_results: Dict):
        """평가 결과 요약 출력"""
        print("\n" + "=" * 80)
        print("평가 결과 요약")
        print("=" * 80)
        
        for method, results in all_results.items():
            print(f"\n[{method.upper()}]")
            print("-" * 80)
            
            aggregate = self.calculate_aggregate_metrics(results)
            
            print(f"{'지표':<30} {'값':>15}")
            print("-" * 50)
            print(f"{'Precision@1':<30} {aggregate.get('precision@1', 0):.4f}")
            print(f"{'Precision@3':<30} {aggregate.get('precision@3', 0):.4f}")
            print(f"{'Precision@5':<30} {aggregate.get('precision@5', 0):.4f}")
            print(f"{'Recall@3':<30} {aggregate.get('recall@3', 0):.4f}")
            print(f"{'Recall@5':<30} {aggregate.get('recall@5', 0):.4f}")
            print(f"{'F1@3':<30} {aggregate.get('f1@3', 0):.4f}")
            print(f"{'Average Precision':<30} {aggregate.get('average_precision', 0):.4f}")
            print(f"{'Reciprocal Rank':<30} {aggregate.get('reciprocal_rank', 0):.4f}")
            print(f"{'NDCG@3':<30} {aggregate.get('ndcg@3', 0):.4f}")
            print(f"{'Doc Type Coverage':<30} {aggregate.get('doc_type_coverage', 0):.4f}")
            print(f"{'Source Diversity':<30} {aggregate.get('source_diversity', 0):.4f}")
            print(f"{'Avg Query Time (s)':<30} {aggregate.get('query_time', 0):.4f}")
            print()
            
            # 질문 유형별 성능
            by_type = self.calculate_metrics_by_query_type(results)
            print("질문 유형별 Precision@3:")
            for qtype, metrics in by_type.items():
                print(f"  - {qtype:<25} {metrics.get('precision@3', 0):.4f}")
        
        print("\n" + "=" * 80)
