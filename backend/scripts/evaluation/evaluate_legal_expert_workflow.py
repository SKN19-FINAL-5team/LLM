#!/usr/bin/env python3
"""
법률 전문가 관점의 다단계 검색 워크플로우 평가
"""

import json
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.rag.multi_stage_retriever_v2 import MultiStageRetrieverV2
import os
from dotenv import load_dotenv

load_dotenv()


class LegalExpertWorkflowEvaluator:
    """법률 전문가 워크플로우 평가기"""
    
    def __init__(self, test_cases_path: str):
        self.test_cases_path = test_cases_path
        self.test_cases = self._load_test_cases()
        
        # Retriever 초기화
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'ddoksori'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres')
        }
        self.retriever = MultiStageRetrieverV2(db_config)
        
        # 통계
        self.stats = {
            'total_cases': 0,
            'total_steps': 0,
            'successful_steps': 0,
            'failed_steps': 0,
            'by_doc_type': {
                'law': {'total': 0, 'success': 0},
                'case': {'total': 0, 'success': 0},
                'criteria': {'total': 0, 'success': 0}
            }
        }
    
    def _load_test_cases(self) -> List[Dict]:
        with open(self.test_cases_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['test_cases']
    
    def evaluate_single_step(self, step: Dict, case_id: str) -> Dict:
        """단일 검색 단계 평가"""
        query = step['query']
        expected_doc_type = step['expected_doc_type']
        
        # 검색 실행
        response = self.retriever.search(query=query, top_k=5)
        results = response['results']
        
        # 결과 분석
        doc_types = [r['doc_type'] for r in results]
        has_expected_type = expected_doc_type in doc_types
        
        # 키워드 매칭 확인
        expected_keywords = step.get('expected_keywords', [])
        keyword_matches = 0
        if expected_keywords and results:
            top_content = results[0]['content'].lower()
            keyword_matches = sum(1 for kw in expected_keywords if kw.lower() in top_content)
        
        # 법령/조문 매칭 확인
        law_match = False
        article_match = False
        if expected_doc_type == 'law':
            expected_law = step.get('expected_law', '')
            expected_article = step.get('expected_article', '')
            
            for r in results:
                if r['doc_type'] == 'law':
                    if expected_law and expected_law in r['content']:
                        law_match = True
                    if expected_article and expected_article in r['content']:
                        article_match = True
        
        success = has_expected_type and (
            not expected_keywords or keyword_matches >= len(expected_keywords) // 2
        )
        
        return {
            'case_id': case_id,
            'step': step['step'],
            'query': query,
            'expected_doc_type': expected_doc_type,
            'actual_doc_types': doc_types,
            'has_expected_type': has_expected_type,
            'keyword_match_ratio': keyword_matches / len(expected_keywords) if expected_keywords else 1.0,
            'law_match': law_match,
            'article_match': article_match,
            'success': success,
            'top_score': results[0]['score'] if results else 0.0,
            'num_results': len(results)
        }
    
    def evaluate_all(self):
        """전체 테스트 케이스 평가"""
        print("=" * 80)
        print("법률 전문가 워크플로우 평가")
        print("=" * 80)
        
        all_results = []
        
        for test_case in self.test_cases:
            case_id = test_case['case_id']
            scenario = test_case['scenario']
            
            print(f"\n{'=' * 80}")
            print(f"[{case_id}] {scenario}")
            print(f"{'=' * 80}")
            print(f"소비자 불만: {test_case['consumer_complaint']}")
            
            self.stats['total_cases'] += 1
            
            for step in test_case['expert_workflow']:
                self.stats['total_steps'] += 1
                
                print(f"\n  [Step {step['step']}] {step['expert_thinking']}")
                print(f"  Query: \"{step['query']}\"")
                
                result = self.evaluate_single_step(step, case_id)
                all_results.append(result)
                
                # 통계 업데이트
                doc_type = step['expected_doc_type']
                self.stats['by_doc_type'][doc_type]['total'] += 1
                
                if result['success']:
                    self.stats['successful_steps'] += 1
                    self.stats['by_doc_type'][doc_type]['success'] += 1
                    status = "✅ SUCCESS"
                else:
                    self.stats['failed_steps'] += 1
                    status = "❌ FAILED"
                
                print(f"  {status}")
                print(f"    - Expected: {result['expected_doc_type']}")
                print(f"    - Actual: {result['actual_doc_types']}")
                print(f"    - Keyword Match: {result['keyword_match_ratio']:.1%}")
                if result['expected_doc_type'] == 'law':
                    print(f"    - Law Match: {'✅' if result['law_match'] else '❌'}")
                    if step.get('expected_article'):
                        print(f"    - Article Match: {'✅' if result['article_match'] else '❌'}")
        
        # 최종 통계
        self._print_final_stats()
        
        # 결과 저장
        self._save_results(all_results)
    
    def _print_final_stats(self):
        print("\n" + "=" * 80)
        print("최종 평가 결과")
        print("=" * 80)
        
        total = self.stats['total_steps']
        success = self.stats['successful_steps']
        success_rate = (success / total * 100) if total > 0 else 0
        
        print(f"\n전체:")
        print(f"  - 테스트 케이스: {self.stats['total_cases']}개")
        print(f"  - 검색 단계: {total}개")
        print(f"  - 성공: {success}개")
        print(f"  - 실패: {self.stats['failed_steps']}개")
        print(f"  - 성공률: {success_rate:.1f}%")
        
        print(f"\n문서 타입별:")
        for doc_type, stats in self.stats['by_doc_type'].items():
            if stats['total'] > 0:
                rate = (stats['success'] / stats['total'] * 100)
                print(f"  - {doc_type}: {stats['success']}/{stats['total']} ({rate:.1f}%)")
    
    def _save_results(self, results: List[Dict]):
        output_path = Path(__file__).parent / f"legal_expert_eval_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'detailed_results': results
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n결과 저장: {output_path}")


def main():
    test_cases_path = Path(__file__).parent / "test_cases_legal_expert.json"
    
    if not test_cases_path.exists():
        print(f"❌ 테스트 케이스 파일이 없습니다: {test_cases_path}")
        return
    
    evaluator = LegalExpertWorkflowEvaluator(str(test_cases_path))
    evaluator.evaluate_all()


if __name__ == "__main__":
    main()
