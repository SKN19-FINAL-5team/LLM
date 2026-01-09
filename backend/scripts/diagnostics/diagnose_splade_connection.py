#!/usr/bin/env python3
"""
SPLADE 연결 상태 진단 스크립트
RunPod API 서버 연결 및 로컬 모드 사용 가능 여부 확인
"""

import os
import sys
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_api_server():
    """RunPod API 서버 연결 확인"""
    print("=" * 60)
    print("1. RunPod API 서버 연결 확인")
    print("=" * 60)
    
    try:
        import requests
        api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
        print(f"   API URL: {api_url}")
        
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"   ✅ 연결 성공!")
                print(f"   응답: {response.json()}")
                return True
            else:
                print(f"   ❌ 응답 오류 (상태 코드: {response.status_code})")
                return False
        except requests.exceptions.ConnectionError:
            print(f"   ❌ 연결 실패: Connection refused")
            print(f"   💡 SSH 터널이 연결되어 있는지 확인하세요:")
            print(f"      ssh -L 8001:localhost:8000 root@[IP] -p [포트] -N")
            return False
        except requests.exceptions.Timeout:
            print(f"   ❌ 연결 시간 초과")
            return False
        except Exception as e:
            print(f"   ❌ 오류: {e}")
            return False
    except ImportError:
        print("   ⚠️  requests 모듈이 없습니다: pip install requests")
        return False


def check_local_mode():
    """로컬 직접 실행 모드 확인"""
    print("\n" + "=" * 60)
    print("2. 로컬 직접 실행 모드 확인")
    print("=" * 60)
    
    try:
        import torch
        torch_version = torch.__version__
        print(f"   PyTorch 버전: {torch_version}")
        
        # 버전 확인
        try:
            major, minor = map(int, torch_version.split('.')[:2])
            if major < 2 or (major == 2 and minor < 6):
                print(f"   ❌ torch 버전이 2.6 미만입니다")
                print(f"   💡 업그레이드: pip install --upgrade torch>=2.6")
                return False
            else:
                print(f"   ✅ torch 버전 OK")
        except:
            print(f"   ⚠️  torch 버전 파싱 실패")
        
        # CUDA 확인
        cuda_available = torch.cuda.is_available()
        print(f"   CUDA 사용 가능: {cuda_available}")
        if cuda_available:
            print(f"   GPU 개수: {torch.cuda.device_count()}")
            print(f"   GPU 이름: {torch.cuda.get_device_name(0)}")
        
        # 모듈 import 확인
        try:
            from splade.test_splade_naver import NaverSPLADEDBRetriever
            print(f"   ✅ NaverSPLADEDBRetriever import 성공")
            return True
        except ImportError as e:
            print(f"   ❌ NaverSPLADEDBRetriever import 실패: {e}")
            return False
        except Exception as e:
            error_str = str(e)
            if "torch.load" in error_str or "torch>=2.6" in error_str:
                print(f"   ❌ torch 버전 문제: {error_str}")
                return False
            else:
                print(f"   ⚠️  모듈 로드 오류: {e}")
                return False
                
    except ImportError:
        print("   ❌ torch가 설치되지 않았습니다")
        return False


def check_environment():
    """환경 변수 확인"""
    print("\n" + "=" * 60)
    print("3. 환경 변수 확인")
    print("=" * 60)
    
    load_dotenv()
    
    api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
    print(f"   SPLADE_API_URL: {api_url}")
    
    hf_token = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')
    if hf_token:
        print(f"   HF_TOKEN: {'설정됨' if hf_token else '설정 안 됨'} (길이: {len(hf_token) if hf_token else 0})")
    else:
        print(f"   HF_TOKEN: 설정 안 됨")
        print(f"   💡 로컬 모드에서는 필요 없지만, RunPod API 서버에는 필요합니다")


def check_modules():
    """필요한 모듈 확인"""
    print("\n" + "=" * 60)
    print("4. 필요한 모듈 확인")
    print("=" * 60)
    
    modules = [
        ('requests', 'requests'),
        ('torch', 'torch'),
        ('sentence_transformers', 'sentence-transformers'),
        ('transformers', 'transformers'),
    ]
    
    for module_name, package_name in modules:
        try:
            __import__(module_name)
            print(f"   ✅ {package_name}")
        except ImportError:
            print(f"   ❌ {package_name} (설치 필요: pip install {package_name})")


def main():
    """메인 진단 함수"""
    print("\n" + "=" * 60)
    print("SPLADE 연결 상태 진단")
    print("=" * 60)
    print()
    
    # 환경 변수 로드
    load_dotenv()
    
    # 각 항목 확인
    api_ok = check_api_server()
    local_ok = check_local_mode()
    check_environment()
    check_modules()
    
    # 종합 결과
    print("\n" + "=" * 60)
    print("종합 결과")
    print("=" * 60)
    
    if api_ok:
        print("✅ RunPod API 서버 사용 가능")
        print("   평가 스크립트 실행 시 SPLADE가 사용됩니다.")
    elif local_ok:
        print("⚠️  RunPod API 서버 사용 불가, 로컬 모드 사용 가능")
        print("   평가 스크립트 실행 시 로컬 모드로 SPLADE가 사용됩니다.")
        print("   (GPU가 없으면 매우 느릴 수 있습니다)")
    else:
        print("❌ SPLADE 사용 불가")
        print("\n해결 방법:")
        if not api_ok:
            print("   1. SSH 터널 연결:")
            print("      ssh -L 8001:localhost:8000 root@[RunPod_IP] -p [포트] -N")
            print("   2. RunPod에서 API 서버 실행 확인:")
            print("      curl http://localhost:8000/health")
        if not local_ok:
            print("   3. torch 업그레이드 (로컬 모드 사용 시):")
            print("      pip install --upgrade torch>=2.6")
    
    print()


if __name__ == "__main__":
    main()
