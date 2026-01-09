"""
FastAPI   
    API .
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_health():
    """  """
    print("=" * 60)
    print("1.   ")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        print()
    except Exception as e:
        print(f" : {str(e)}\n")


def test_search():
    """ API """
    print("=" * 60)
    print("2.  API ")
    print("=" * 60)
    
    payload = {
        "query": "    .",
        "top_k": 3
    }
    
    print(f"Request: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print()
    
    try:
        response = requests.post(f"{BASE_URL}/search", json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f" : {data['results_count']}")
            print()
            
            for idx, result in enumerate(data['results'][:3], 1):
                print(f"[ {idx}]")
                print(f"  : {result.get('case_no', 'N/A')}")
                print(f"  : {result.get('agency', 'N/A')}")
                print(f"   : {result.get('chunk_type', 'N/A')}")
                print(f"  : {result.get('similarity', 0):.4f}")
                print(f"  : {result.get('text', '')[:100]}...")
                print()
        else:
            print(f"Error: {response.text}")
            print()
            
    except Exception as e:
        print(f" : {str(e)}\n")


def test_chat():
    """ API """
    print("=" * 60)
    print("3.  API ")
    print("=" * 60)
    
    payload = {
        "message": "      ?",
        "top_k": 5
    }
    
    print(f"Request: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print()
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n[]")
            print("-" * 60)
            print(data['answer'])
            print("-" * 60)
            print(f"\n[]")
            print(f"  : {data['model']}")
            print(f"   : {data['chunks_used']}")
            print(f"    : {len(data['sources'])}")
            print()
        else:
            print(f"Error: {response.text}")
            print()
            
    except Exception as e:
        print(f" : {str(e)}\n")


def main():
    """  """
    print("\n" + "=" * 60)
    print("FastAPI   ")
    print("=" * 60)
    print("     : uvicorn app.main:app --reload")
    print("=" * 60 + "\n")
    
    # 1.  
    test_health()
    
    # 2.  API
    test_search()
    
    # 3.  API (OpenAI API  )
    print("   API  OpenAI API  .")
    user_input = input(" API ? (y/n): ")
    if user_input.lower() == 'y':
        test_chat()
    else:
        print(" API  .\n")
    
    print("=" * 60)
    print("  !")
    print("=" * 60)


if __name__ == "__main__":
    main()
