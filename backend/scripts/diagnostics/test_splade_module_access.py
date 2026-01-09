"""
SPLADE 모듈 접근 가능 여부 테스트 스크립트
torch 버전, sentence-transformers, 모델 로드 가능 여부 등을 확인
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_torch():
    """torch 버전 및 CUDA 확인"""
    print("=" * 80)
    print("1. PyTorch 확인")
    print("=" * 80)
    try:
        import torch
        version = torch.__version__
        print(f"✅ torch 버전: {version}")
        
        # 버전 파싱
        try:
            major, minor = map(int, version.split('.')[:2])
            if major < 2 or (major == 2 and minor < 6):
                print(f"⚠️  torch 버전이 2.6 미만입니다 (현재: {version})")
                print("   SPLADE 모델 로드 시 torch.load 보안 취약점으로 인해 실패할 수 있습니다.")
                return False, version
            else:
                print(f"✅ torch 버전이 2.6 이상입니다 (현재: {version})")
                return True, version
        except:
            print(f"⚠️  torch 버전 파싱 실패: {version}")
            return False, version
        
    except ImportError:
        print("❌ torch가 설치되지 않았습니다.")
        return False, None

def test_cuda():
    """CUDA 사용 가능 여부 확인"""
    print("\n" + "=" * 80)
    print("2. CUDA 확인")
    print("=" * 80)
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        print(f"CUDA 사용 가능: {cuda_available}")
        
        if cuda_available:
            print(f"CUDA 버전: {torch.version.cuda}")
            print(f"GPU 개수: {torch.cuda.device_count()}")
            if torch.cuda.device_count() > 0:
                print(f"GPU 이름: {torch.cuda.get_device_name(0)}")
        else:
            print("⚠️  GPU를 사용할 수 없습니다. CPU 모드로 실행됩니다.")
        
        return cuda_available
    except ImportError:
        print("❌ torch가 설치되지 않아 CUDA를 확인할 수 없습니다.")
        return False

def test_sentence_transformers():
    """sentence-transformers 버전 확인"""
    print("\n" + "=" * 80)
    print("3. sentence-transformers 확인")
    print("=" * 80)
    try:
        import sentence_transformers
        version = sentence_transformers.__version__
        print(f"✅ sentence-transformers 버전: {version}")
        
        # 버전 파싱
        try:
            major = int(version.split('.')[0])
            if major < 5:
                print(f"⚠️  sentence-transformers 버전이 5.0.0 미만입니다 (현재: {version})")
                print("   SparseEncoder를 사용할 수 없습니다.")
                return False, version
            else:
                print(f"✅ sentence-transformers 버전이 5.0.0 이상입니다 (현재: {version})")
                return True, version
        except:
            print(f"⚠️  버전 파싱 실패: {version}")
            return False, version
    except ImportError:
        print("❌ sentence-transformers가 설치되지 않았습니다.")
        return False, None

def test_sparse_encoder():
    """SparseEncoder import 테스트"""
    print("\n" + "=" * 80)
    print("4. SparseEncoder Import 테스트")
    print("=" * 80)
    try:
        from sentence_transformers import SparseEncoder
        print("✅ SparseEncoder import 성공")
        return True
    except ImportError as e:
        print(f"❌ SparseEncoder import 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ SparseEncoder import 오류: {e}")
        return False

def test_transformers():
    """transformers 라이브러리 확인"""
    print("\n" + "=" * 80)
    print("5. transformers 확인")
    print("=" * 80)
    try:
        import transformers
        version = transformers.__version__
        print(f"✅ transformers 버전: {version}")
        
        # PreTrainedModel import 테스트
        try:
            from transformers import PreTrainedModel
            print("✅ PreTrainedModel import 성공")
            return True, version
        except ImportError as e:
            print(f"❌ PreTrainedModel import 실패: {e}")
            print("   transformers 라이브러리가 손상되었을 수 있습니다.")
            return False, version
    except ImportError:
        print("❌ transformers가 설치되지 않았습니다.")
        return False, None

def test_api_server():
    """API 서버 연결 테스트"""
    print("\n" + "=" * 80)
    print("6. SPLADE API 서버 연결 테스트")
    print("=" * 80)
    try:
        import requests
        from dotenv import load_dotenv
        
        # 환경 변수 로드
        backend_dir = Path(__file__).parent.parent
        env_file = backend_dir / '.env'
        if env_file.exists():
            load_dotenv(env_file)
        
        api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
        print(f"API URL: {api_url}")
        
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ API 서버 연결 성공 ({api_url})")
                data = response.json()
                print(f"   상태: {data.get('status', 'unknown')}")
                print(f"   디바이스: {data.get('device', 'unknown')}")
                return True
            else:
                print(f"⚠️  API 서버 응답 오류 (상태 코드: {response.status_code})")
                return False
        except requests.exceptions.RequestException as e:
            print(f"⚠️  API 서버 연결 실패: {e}")
            print("   SSH 터널이 연결되어 있는지 확인하세요.")
            return False
    except ImportError:
        print("⚠️  requests가 설치되지 않아 API 서버 테스트를 건너뜁니다.")
        return None

def test_model_load():
    """모델 로드 가능 여부 테스트 (실제 로드는 하지 않음)"""
    print("\n" + "=" * 80)
    print("7. 모델 로드 가능 여부 테스트")
    print("=" * 80)
    
    # torch 버전 확인
    torch_ok, torch_version = test_torch()
    if not torch_ok:
        print("⚠️  torch 버전이 2.6 미만이므로 모델 로드가 실패할 수 있습니다.")
        print("   실제 모델 로드는 시도하지 않습니다.")
        return False
    
    # SparseEncoder 확인
    if not test_sparse_encoder():
        print("⚠️  SparseEncoder를 사용할 수 없으므로 모델 로드가 불가능합니다.")
        return False
    
    # HuggingFace 토큰 확인
    from dotenv import load_dotenv
    backend_dir = Path(__file__).parent.parent
    env_file = backend_dir / '.env'
    if env_file.exists():
        load_dotenv(env_file)
    
    HF_TOKEN = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')
    if not HF_TOKEN:
        print("⚠️  HF_TOKEN이 설정되지 않았습니다.")
        print("   모델 접근 권한이 필요할 수 있습니다.")
    else:
        print("✅ HF_TOKEN이 설정되어 있습니다.")
    
    print("✅ 모델 로드 가능 (실제 로드는 하지 않음)")
    return True

def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 80)
    print("SPLADE 모듈 접근 가능 여부 테스트")
    print("=" * 80)
    print()
    
    results = {
        'torch': False,
        'cuda': False,
        'sentence_transformers': False,
        'sparse_encoder': False,
        'transformers': False,
        'api_server': None,
        'model_load': False
    }
    
    # 1. torch 테스트
    results['torch'], torch_version = test_torch()
    
    # 2. CUDA 테스트
    results['cuda'] = test_cuda()
    
    # 3. sentence-transformers 테스트
    results['sentence_transformers'], st_version = test_sentence_transformers()
    
    # 4. SparseEncoder 테스트
    results['sparse_encoder'] = test_sparse_encoder()
    
    # 5. transformers 테스트
    results['transformers'], tf_version = test_transformers()
    
    # 6. API 서버 테스트
    results['api_server'] = test_api_server()
    
    # 7. 모델 로드 가능 여부 테스트
    results['model_load'] = test_model_load()
    
    # 최종 요약
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    
    print(f"\n✅ 통과:")
    if results['torch']:
        print(f"  - torch ({torch_version})")
    if results['sentence_transformers']:
        print(f"  - sentence-transformers ({st_version})")
    if results['sparse_encoder']:
        print("  - SparseEncoder import")
    if results['transformers']:
        print(f"  - transformers ({tf_version})")
    if results['cuda']:
        print("  - CUDA 사용 가능")
    if results['api_server']:
        print("  - API 서버 연결")
    if results['model_load']:
        print("  - 모델 로드 가능")
    
    print(f"\n⚠️  경고:")
    if not results['torch']:
        print("  - torch 버전이 2.6 미만 (모델 로드 실패 가능)")
    if not results['sentence_transformers']:
        print("  - sentence-transformers 버전이 5.0.0 미만 (SparseEncoder 사용 불가)")
    if not results['sparse_encoder']:
        print("  - SparseEncoder import 실패")
    if not results['transformers']:
        print("  - transformers 라이브러리 문제")
    if not results['cuda']:
        print("  - CUDA 사용 불가 (CPU 모드로 실행)")
    if results['api_server'] is False:
        print("  - API 서버 연결 실패 (로컬 모드 사용 필요)")
    if not results['model_load']:
        print("  - 모델 로드 불가능")
    
    # 최종 권장사항
    print("\n" + "=" * 80)
    print("권장사항")
    print("=" * 80)
    
    if not results['torch']:
        print("\n1. torch 업그레이드:")
        print("   pip install --upgrade torch>=2.6")
    
    if not results['sentence_transformers']:
        print("\n2. sentence-transformers 업그레이드:")
        print("   pip install --upgrade sentence-transformers>=5.0.0")
    
    if results['api_server'] is False:
        print("\n3. API 서버 연결:")
        print("   - RunPod에 SPLADE API 서버 실행")
        print("   - 로컬에서 SSH 터널 연결: ssh -L 8001:localhost:8000 [user]@[host] -p [port]")
        print("   - 또는 로컬에서 torch>=2.6으로 업그레이드 후 직접 실행")
    
    if results['model_load']:
        print("\n✅ SPLADE 모델을 사용할 수 있습니다!")
    else:
        print("\n⚠️  SPLADE 모델을 사용할 수 없습니다.")
        print("   위의 권장사항을 따라 수정하세요.")
    
    return results

if __name__ == "__main__":
    main()
