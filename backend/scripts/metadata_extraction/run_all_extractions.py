#!/usr/bin/env python3
"""
       
"""

import sys
from pathlib import Path

#   Python  
sys.path.append(str(Path(__file__).parent))

from extract_law_metadata import LawMetadataExtractor, DB_CONFIG
from extract_criteria_metadata import CriteriaMetadataExtractor
from extract_case_metadata import CaseMetadataExtractor


def main():
    """   """
    
    print("="*60)
    print("   ")
    print("="*60)
    print()
    
    success_count = 0
    total_count = 3
    
    # 1.   
    try:
        print("\n" + "#"*60)
        print("# 1/3:   ")
        print("#"*60)
        law_extractor = LawMetadataExtractor(DB_CONFIG)
        law_extractor.run()
        success_count += 1
    except Exception as e:
        print(f"    : {e}")
    
    # 2.   
    try:
        print("\n" + "#"*60)
        print("# 2/3:   ")
        print("#"*60)
        criteria_extractor = CriteriaMetadataExtractor(DB_CONFIG)
        criteria_extractor.run()
        success_count += 1
    except Exception as e:
        print(f"    : {e}")
    
    # 3.   
    try:
        print("\n" + "#"*60)
        print("# 3/3:   ")
        print("#"*60)
        case_extractor = CaseMetadataExtractor(DB_CONFIG)
        case_extractor.run()
        success_count += 1
    except Exception as e:
        print(f"    : {e}")
    
    #  
    print("\n" + "="*60)
    print("   ")
    print("="*60)
    print(f": {success_count}/{total_count}")
    if success_count == total_count:
        print("     !")
    else:
        print(f"     .")
    print("="*60)
    
    return success_count == total_count


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
