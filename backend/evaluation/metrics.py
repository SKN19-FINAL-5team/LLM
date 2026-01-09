"""
  - RAG    
: 2026-01-05
"""

import math
from typing import List, Set, Dict
from collections import Counter


class EvaluationMetrics:
    """RAG   """
    
    @staticmethod
    def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
        """
        Precision@K 
        
        Args:
            retrieved:   ID  ()
            relevant:    ID 
            k:  K
        
        Returns:
            Precision@K  (0.0 ~ 1.0)
        """
        if k <= 0 or not retrieved:
            return 0.0
        
        top_k = retrieved[:k]
        relevant_in_top_k = sum(1 for chunk_id in top_k if chunk_id in relevant)
        
        return relevant_in_top_k / k
    
    @staticmethod
    def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
        """
        Recall@K 
        
        Args:
            retrieved:   ID  ()
            relevant:    ID 
            k:  K
        
        Returns:
            Recall@K  (0.0 ~ 1.0)
        """
        if not relevant or k <= 0 or not retrieved:
            return 0.0
        
        top_k = retrieved[:k]
        relevant_in_top_k = sum(1 for chunk_id in top_k if chunk_id in relevant)
        
        return relevant_in_top_k / len(relevant)
    
    @staticmethod
    def f1_score_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
        """
        F1-Score@K 
        
        Args:
            retrieved:   ID  ()
            relevant:    ID 
            k:  K
        
        Returns:
            F1-Score@K  (0.0 ~ 1.0)
        """
        precision = EvaluationMetrics.precision_at_k(retrieved, relevant, k)
        recall = EvaluationMetrics.recall_at_k(retrieved, relevant, k)
        
        if precision + recall == 0:
            return 0.0
        
        return 2 * (precision * recall) / (precision + recall)
    
    @staticmethod
    def average_precision(retrieved: List[str], relevant: Set[str]) -> float:
        """
        Average Precision (AP) 
        
        Args:
            retrieved:   ID  ()
            relevant:    ID 
        
        Returns:
            AP  (0.0 ~ 1.0)
        """
        if not relevant or not retrieved:
            return 0.0
        
        score = 0.0
        num_relevant_found = 0
        
        for i, chunk_id in enumerate(retrieved):
            if chunk_id in relevant:
                num_relevant_found += 1
                precision_at_i = num_relevant_found / (i + 1)
                score += precision_at_i
        
        return score / len(relevant)
    
    @staticmethod
    def mean_average_precision(all_retrieved: List[List[str]], all_relevant: List[Set[str]]) -> float:
        """
        Mean Average Precision (MAP) 
        
        Args:
            all_retrieved:      
            all_relevant:       
        
        Returns:
            MAP  (0.0 ~ 1.0)
        """
        if not all_retrieved or not all_relevant:
            return 0.0
        
        if len(all_retrieved) != len(all_relevant):
            raise ValueError("retrieved relevant  .")
        
        ap_scores = []
        for retrieved, relevant in zip(all_retrieved, all_relevant):
            ap = EvaluationMetrics.average_precision(retrieved, relevant)
            ap_scores.append(ap)
        
        return sum(ap_scores) / len(ap_scores)
    
    @staticmethod
    def reciprocal_rank(retrieved: List[str], relevant: Set[str]) -> float:
        """
        Reciprocal Rank (RR) 
        
        Args:
            retrieved:   ID  ()
            relevant:    ID 
        
        Returns:
            RR  (0.0 ~ 1.0)
        """
        if not relevant or not retrieved:
            return 0.0
        
        for i, chunk_id in enumerate(retrieved):
            if chunk_id in relevant:
                return 1.0 / (i + 1)
        
        return 0.0
    
    @staticmethod
    def mean_reciprocal_rank(all_retrieved: List[List[str]], all_relevant: List[Set[str]]) -> float:
        """
        Mean Reciprocal Rank (MRR) 
        
        Args:
            all_retrieved:      
            all_relevant:       
        
        Returns:
            MRR  (0.0 ~ 1.0)
        """
        if not all_retrieved or not all_relevant:
            return 0.0
        
        if len(all_retrieved) != len(all_relevant):
            raise ValueError("retrieved relevant  .")
        
        rr_scores = []
        for retrieved, relevant in zip(all_retrieved, all_relevant):
            rr = EvaluationMetrics.reciprocal_rank(retrieved, relevant)
            rr_scores.append(rr)
        
        return sum(rr_scores) / len(rr_scores)
    
    @staticmethod
    def dcg_at_k(retrieved: List[str], relevance_scores: Dict[str, int], k: int) -> float:
        """
        Discounted Cumulative Gain@K (DCG@K) 
        
        Args:
            retrieved:   ID  ()
            relevance_scores:     (0, 1, 2)
            k:  K
        
        Returns:
            DCG@K 
        """
        if k <= 0 or not retrieved:
            return 0.0
        
        dcg = 0.0
        for i, chunk_id in enumerate(retrieved[:k]):
            rel = relevance_scores.get(chunk_id, 0)
            dcg += rel / math.log2(i + 2)  # i+2 because index starts at 0
        
        return dcg
    
    @staticmethod
    def ndcg_at_k(retrieved: List[str], relevance_scores: Dict[str, int], k: int) -> float:
        """
        Normalized Discounted Cumulative Gain@K (NDCG@K) 
        
        Args:
            retrieved:   ID  ()
            relevance_scores:     (0, 1, 2)
            k:  K
        
        Returns:
            NDCG@K  (0.0 ~ 1.0)
        """
        dcg = EvaluationMetrics.dcg_at_k(retrieved, relevance_scores, k)
        
        # Ideal DCG  (   )
        ideal_order = sorted(relevance_scores.items(), key=lambda x: x[1], reverse=True)
        ideal_retrieved = [chunk_id for chunk_id, _ in ideal_order]
        idcg = EvaluationMetrics.dcg_at_k(ideal_retrieved, relevance_scores, k)
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    @staticmethod
    def document_type_coverage(
        retrieved_doc_types: List[str],
        expected_doc_types: Set[str]
    ) -> float:
        """
        Document Type Coverage 
        
        Args:
            retrieved_doc_types:    
            expected_doc_types:    
        
        Returns:
            Coverage  (0.0 ~ 1.0)
        """
        if not expected_doc_types:
            return 1.0
        
        found_types = set(retrieved_doc_types) & expected_doc_types
        return len(found_types) / len(expected_doc_types)
    
    @staticmethod
    def source_diversity(retrieved_sources: List[str]) -> float:
        """
        Source Diversity  (Shannon Entropy)
        
        Args:
            retrieved_sources:    
        
        Returns:
            Diversity  (0.0 ~ log2(N), N   )
        """
        if not retrieved_sources:
            return 0.0
        
        #   
        source_counts = Counter(retrieved_sources)
        total = len(retrieved_sources)
        
        # Shannon Entropy 
        entropy = 0.0
        for count in source_counts.values():
            p = count / total
            entropy -= p * math.log2(p)
        
        return entropy
    
    @staticmethod
    def context_relevance(
        expanded_chunk_ids: List[str],
        relevant_chunk_ids: Set[str]
    ) -> float:
        """
        Context Relevance  (  )
        
        Args:
            expanded_chunk_ids:   ID 
            relevant_chunk_ids:    ID 
        
        Returns:
            Relevance  (0.0 ~ 1.0)
        """
        if not expanded_chunk_ids:
            return 0.0
        
        relevant_count = sum(1 for chunk_id in expanded_chunk_ids if chunk_id in relevant_chunk_ids)
        return relevant_count / len(expanded_chunk_ids)


def calculate_all_metrics(
    retrieved: List[str],
    relevant: Set[str],
    highly_relevant: Set[str],
    expected_doc_types: Set[str],
    retrieved_doc_types: List[str],
    retrieved_sources: List[str],
    query_time: float,
    k_values: List[int] = [1, 3, 5, 10]
) -> Dict:
    """
         
    
    Args:
        retrieved:   ID 
        relevant:    ID 
        highly_relevant:     ID 
        expected_doc_types:    
        retrieved_doc_types:    
        retrieved_sources:    
        query_time:   ()
        k_values:  K  
    
    Returns:
           
    """
    metrics = {}
    
    # Precision, Recall, F1-Score@K
    for k in k_values:
        metrics[f'precision@{k}'] = EvaluationMetrics.precision_at_k(retrieved, relevant, k)
        metrics[f'recall@{k}'] = EvaluationMetrics.recall_at_k(retrieved, relevant, k)
        metrics[f'f1@{k}'] = EvaluationMetrics.f1_score_at_k(retrieved, relevant, k)
    
    # AP, RR
    metrics['average_precision'] = EvaluationMetrics.average_precision(retrieved, relevant)
    metrics['reciprocal_rank'] = EvaluationMetrics.reciprocal_rank(retrieved, relevant)
    
    # NDCG@K ( : highly_relevant=2, relevant=1, =0)
    relevance_scores = {}
    for chunk_id in highly_relevant:
        relevance_scores[chunk_id] = 2
    for chunk_id in relevant:
        if chunk_id not in relevance_scores:
            relevance_scores[chunk_id] = 1
    
    for k in k_values:
        metrics[f'ndcg@{k}'] = EvaluationMetrics.ndcg_at_k(retrieved, relevance_scores, k)
    
    # Document Type Coverage
    metrics['doc_type_coverage'] = EvaluationMetrics.document_type_coverage(
        retrieved_doc_types, expected_doc_types
    )
    
    # Source Diversity
    metrics['source_diversity'] = EvaluationMetrics.source_diversity(retrieved_sources)
    
    # Query Time
    metrics['query_time'] = query_time
    
    return metrics
