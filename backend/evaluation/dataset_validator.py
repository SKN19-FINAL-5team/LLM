"""
똑소리 프로젝트 - 골드 데이터셋 검증 도구
작성일: 2026-01-05
"""

import json
from typing import List, Dict, Tuple
from pathlib import Path


class DatasetValidator:
    """골드 데이터셋 검증"""
    
    REQUIRED_FIELDS = [
        "query_id",
        "query",
        "query_type",
        "expected_doc_types",
        "relevant_chunk_ids",
        "highly_relevant_chunk_ids",
        "irrelevant_chunk_ids",
        "metadata"
    ]
    
    VALID_QUERY_TYPES = [
        "general_inquiry",
        "legal_interpretation",
        "similar_case"
    ]
    
    VALID_DOC_TYPES = [
        "law",
        "counsel_case",
        "mediation_case"
    ]
    
    VALID_DIFFICULTIES = [
        "easy",
        "medium",
        "hard"
    ]
    
    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path
        self.dataset = []
        self.errors = []
        self.warnings = []
    
    def load_dataset(self) -> bool:
        """데이터셋 로드"""
        try:
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                self.dataset = json.load(f)
            return True
        except Exception as e:
            self.errors.append(f"파일 로드 실패: {e}")
            return False
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        데이터셋 검증
        
        Returns:
            (검증 성공 여부, 오류 목록, 경고 목록)
        """
        if not self.load_dataset():
            return False, self.errors, self.warnings
        
        if not isinstance(self.dataset, list):
            self.errors.append("데이터셋은 리스트 형식이어야 합니다.")
            return False, self.errors, self.warnings
        
        if len(self.dataset) == 0:
            self.warnings.append("데이터셋이 비어있습니다.")
        
        # 각 항목 검증
        for idx, item in enumerate(self.dataset):
            self._validate_item(idx, item)
        
        # query_id 중복 검사
        self._check_duplicate_query_ids()
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings
    
    def _validate_item(self, idx: int, item: Dict):
        """개별 항목 검증"""
        # 필수 필드 확인
        for field in self.REQUIRED_FIELDS:
            if field not in item:
                self.errors.append(f"[{idx}] 필수 필드 누락: {field}")
        
        if "query_id" in item and not isinstance(item["query_id"], str):
            self.errors.append(f"[{idx}] query_id는 문자열이어야 합니다.")
        
        if "query" in item:
            if not isinstance(item["query"], str):
                self.errors.append(f"[{idx}] query는 문자열이어야 합니다.")
            elif len(item["query"].strip()) == 0:
                self.errors.append(f"[{idx}] query가 비어있습니다.")
        
        if "query_type" in item:
            if item["query_type"] not in self.VALID_QUERY_TYPES:
                self.errors.append(
                    f"[{idx}] 잘못된 query_type: {item['query_type']}. "
                    f"유효한 값: {self.VALID_QUERY_TYPES}"
                )
        
        if "expected_doc_types" in item:
            if not isinstance(item["expected_doc_types"], list):
                self.errors.append(f"[{idx}] expected_doc_types는 리스트여야 합니다.")
            else:
                for doc_type in item["expected_doc_types"]:
                    if doc_type not in self.VALID_DOC_TYPES:
                        self.errors.append(
                            f"[{idx}] 잘못된 doc_type: {doc_type}. "
                            f"유효한 값: {self.VALID_DOC_TYPES}"
                        )
        
        # 청크 ID 리스트 검증
        for field in ["relevant_chunk_ids", "highly_relevant_chunk_ids", "irrelevant_chunk_ids"]:
            if field in item:
                if not isinstance(item[field], list):
                    self.errors.append(f"[{idx}] {field}는 리스트여야 합니다.")
        
        # relevant_chunk_ids가 비어있으면 경고
        if "relevant_chunk_ids" in item and len(item["relevant_chunk_ids"]) == 0:
            self.warnings.append(f"[{idx}] relevant_chunk_ids가 비어있습니다.")
        
        # highly_relevant는 relevant의 부분집합이어야 함
        if "relevant_chunk_ids" in item and "highly_relevant_chunk_ids" in item:
            relevant_set = set(item["relevant_chunk_ids"])
            highly_relevant_set = set(item["highly_relevant_chunk_ids"])
            if not highly_relevant_set.issubset(relevant_set):
                self.errors.append(
                    f"[{idx}] highly_relevant_chunk_ids는 relevant_chunk_ids의 부분집합이어야 합니다."
                )
        
        # 메타데이터 검증
        if "metadata" in item:
            metadata = item["metadata"]
            if not isinstance(metadata, dict):
                self.errors.append(f"[{idx}] metadata는 딕셔너리여야 합니다.")
            else:
                if "difficulty" in metadata:
                    if metadata["difficulty"] not in self.VALID_DIFFICULTIES:
                        self.errors.append(
                            f"[{idx}] 잘못된 difficulty: {metadata['difficulty']}. "
                            f"유효한 값: {self.VALID_DIFFICULTIES}"
                        )
    
    def _check_duplicate_query_ids(self):
        """query_id 중복 검사"""
        query_ids = [item.get("query_id") for item in self.dataset if "query_id" in item]
        seen = set()
        duplicates = set()
        
        for qid in query_ids:
            if qid in seen:
                duplicates.add(qid)
            seen.add(qid)
        
        if duplicates:
            self.errors.append(f"중복된 query_id: {duplicates}")
    
    def print_report(self):
        """검증 결과 리포트 출력"""
        print("\n" + "=" * 60)
        print("데이터셋 검증 리포트")
        print("=" * 60)
        print(f"파일: {self.dataset_path}")
        print(f"총 항목 수: {len(self.dataset)}")
        print()
        
        if self.errors:
            print(f"❌ 오류 {len(self.errors)}개:")
            for error in self.errors:
                print(f"  - {error}")
            print()
        
        if self.warnings:
            print(f"⚠️  경고 {len(self.warnings)}개:")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()
        
        if not self.errors and not self.warnings:
            print("✅ 검증 통과! 오류 및 경고 없음.")
        elif not self.errors:
            print("✅ 검증 통과! (경고 있음)")
        else:
            print("❌ 검증 실패!")
        
        print("=" * 60)


def main():
    """메인 실행 함수"""
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python dataset_validator.py <dataset_path>")
        print("예시: python dataset_validator.py datasets/gold_v1.json")
        return
    
    dataset_path = sys.argv[1]
    
    if not Path(dataset_path).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {dataset_path}")
        return
    
    validator = DatasetValidator(dataset_path)
    is_valid, errors, warnings = validator.validate()
    validator.print_report()
    
    # 검증 실패 시 종료 코드 1 반환
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
