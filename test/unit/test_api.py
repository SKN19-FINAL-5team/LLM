"""
FastAPI 엔드포인트 테스트 스크립트
서버가 실행 중일 때 API를 테스트합니다.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_health():
    """헬스 체크 테스트"""
    print("=" * 60)
    print("1. 헬스 체크 테스트")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        print()
    except Exception as e:
        print(f"❌ 오류: {str(e)}\n")


def test_search():
    """검색 API 테스트"""
    print("=" * 60)
    print("2. 검색 API 테스트")
    print("=" * 60)
    
    payload = {
        "query": "에어컨 설치 불량으로 누수가 발생했습니다.",
        "top_k": 3
    }
    
    print(f"Request: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print()
    
    try:
        response = requests.post(f"{BASE_URL}/search", json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"검색 결과: {data['results_count']}개")
            print()
            
            for idx, result in enumerate(data['results'][:3], 1):
                print(f"[결과 {idx}]")
                print(f"  사건번호: {result.get('case_no', 'N/A')}")
                print(f"  기관: {result.get('agency', 'N/A')}")
                print(f"  청크 타입: {result.get('chunk_type', 'N/A')}")
                print(f"  유사도: {result.get('similarity', 0):.4f}")
                print(f"  내용: {result.get('text', '')[:100]}...")
                print()
        else:
            print(f"Error: {response.text}")
            print()
            
    except Exception as e:
        print(f"❌ 오류: {str(e)}\n")


def test_chat():
    """챗봇 API 테스트"""
    print("=" * 60)
    print("3. 챗봇 API 테스트")
    print("=" * 60)
    
    payload = {
        "message": "휴대폰 액정이 자연 파손되었는데 무상 수리가 가능한가요?",
        "top_k": 5
    }
    
    print(f"Request: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print()
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n[답변]")
            print("-" * 60)
            print(data['answer'])
            print("-" * 60)
            print(f"\n[메타데이터]")
            print(f"  모델: {data['model']}")
            print(f"  사용된 청크: {data['chunks_used']}개")
            print(f"  참고 사례 수: {len(data['sources'])}개")
            print()
        else:
            print(f"Error: {response.text}")
            print()
            
    except Exception as e:
        print(f"❌ 오류: {str(e)}\n")


def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("FastAPI 엔드포인트 테스트 시작")
    print("=" * 60)
    print("⚠️  서버가 실행 중이어야 합니다: uvicorn app.main:app --reload")
    print("=" * 60 + "\n")
    
    # 1. 헬스 체크
    test_health()
    
    # 2. 검색 API
    test_search()
    
    # 3. 챗봇 API (OpenAI API 키 필요)
    print("⚠️  챗봇 API 테스트는 OpenAI API 키가 필요합니다.")
    user_input = input("챗봇 API를 테스트하시겠습니까? (y/n): ")
    if user_input.lower() == 'y':
        test_chat()
    else:
        print("챗봇 API 테스트를 건너뜁니다.\n")
    
    print("=" * 60)
    print("모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
