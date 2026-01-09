"""
  -    
: 2026-01-05
"""

import json
from typing import List, Dict, Tuple
from pathlib import Path


class DatasetValidator:
    """  """
    
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
        """ """
        try:
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                self.dataset = json.load(f)
            return True
        except Exception as e:
            self.errors.append(f"  : {e}")
            return False
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
         
        
        Returns:
            (  ,  ,  )
        """
        if not self.load_dataset():
            return False, self.errors, self.warnings
        
        if not isinstance(self.dataset, list):
            self.errors.append("   .")
            return False, self.errors, self.warnings
        
        if len(self.dataset) == 0:
            self.warnings.append(" .")
        
        #   
        for idx, item in enumerate(self.dataset):
            self._validate_item(idx, item)
        
        # query_id  
        self._check_duplicate_query_ids()
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings
    
    def _validate_item(self, idx: int, item: Dict):
        """  """
        #   
        for field in self.REQUIRED_FIELDS:
            if field not in item:
                self.errors.append(f"[{idx}]   : {field}")
        
        if "query_id" in item and not isinstance(item["query_id"], str):
            self.errors.append(f"[{idx}] query_id  .")
        
        if "query" in item:
            if not isinstance(item["query"], str):
                self.errors.append(f"[{idx}] query  .")
            elif len(item["query"].strip()) == 0:
                self.errors.append(f"[{idx}] query .")
        
        if "query_type" in item:
            if item["query_type"] not in self.VALID_QUERY_TYPES:
                self.errors.append(
                    f"[{idx}]  query_type: {item['query_type']}. "
                    f" : {self.VALID_QUERY_TYPES}"
                )
        
        if "expected_doc_types" in item:
            if not isinstance(item["expected_doc_types"], list):
                self.errors.append(f"[{idx}] expected_doc_types  .")
            else:
                for doc_type in item["expected_doc_types"]:
                    if doc_type not in self.VALID_DOC_TYPES:
                        self.errors.append(
                            f"[{idx}]  doc_type: {doc_type}. "
                            f" : {self.VALID_DOC_TYPES}"
                        )
        
        #  ID  
        for field in ["relevant_chunk_ids", "highly_relevant_chunk_ids", "irrelevant_chunk_ids"]:
            if field in item:
                if not isinstance(item[field], list):
                    self.errors.append(f"[{idx}] {field}  .")
        
        # relevant_chunk_ids  
        if "relevant_chunk_ids" in item and len(item["relevant_chunk_ids"]) == 0:
            self.warnings.append(f"[{idx}] relevant_chunk_ids .")
        
        # highly_relevant relevant  
        if "relevant_chunk_ids" in item and "highly_relevant_chunk_ids" in item:
            relevant_set = set(item["relevant_chunk_ids"])
            highly_relevant_set = set(item["highly_relevant_chunk_ids"])
            if not highly_relevant_set.issubset(relevant_set):
                self.errors.append(
                    f"[{idx}] highly_relevant_chunk_ids relevant_chunk_ids  ."
                )
        
        #  
        if "metadata" in item:
            metadata = item["metadata"]
            if not isinstance(metadata, dict):
                self.errors.append(f"[{idx}] metadata  .")
            else:
                if "difficulty" in metadata:
                    if metadata["difficulty"] not in self.VALID_DIFFICULTIES:
                        self.errors.append(
                            f"[{idx}]  difficulty: {metadata['difficulty']}. "
                            f" : {self.VALID_DIFFICULTIES}"
                        )
    
    def _check_duplicate_query_ids(self):
        """query_id  """
        query_ids = [item.get("query_id") for item in self.dataset if "query_id" in item]
        seen = set()
        duplicates = set()
        
        for qid in query_ids:
            if qid in seen:
                duplicates.add(qid)
            seen.add(qid)
        
        if duplicates:
            self.errors.append(f" query_id: {duplicates}")
    
    def print_report(self):
        """   """
        print("\n" + "=" * 60)
        print("  ")
        print("=" * 60)
        print(f": {self.dataset_path}")
        print(f"  : {len(self.dataset)}")
        print()
        
        if self.errors:
            print(f"  {len(self.errors)}:")
            for error in self.errors:
                print(f"  - {error}")
            print()
        
        if self.warnings:
            print(f"   {len(self.warnings)}:")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()
        
        if not self.errors and not self.warnings:
            print("  !    .")
        elif not self.errors:
            print("  ! ( )")
        else:
            print("  !")
        
        print("=" * 60)


def main():
    """  """
    import sys
    
    if len(sys.argv) < 2:
        print(": python dataset_validator.py <dataset_path>")
        print(": python dataset_validator.py datasets/gold_v1.json")
        return
    
    dataset_path = sys.argv[1]
    
    if not Path(dataset_path).exists():
        print(f"    : {dataset_path}")
        return
    
    validator = DatasetValidator(dataset_path)
    is_valid, errors, warnings = validator.validate()
    validator.print_report()
    
    #      1 
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
