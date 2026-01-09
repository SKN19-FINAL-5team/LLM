"""
HuggingFace 접근 확인 스크립트
naver/splade-v3 모델 접근 가능 여부 확인
"""

import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# 환경 변수 로드
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = Path(__file__).parent.parent.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# HuggingFace 토큰 확인
HF_TOKEN = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')


def check_hf_access():
    """HuggingFace 모델 접근 확인"""
    print("=" * 80)
    print("HuggingFace 접근 확인")
    print("=" * 80)
    
    model_name = "naver/splade-v3"
    print(f"\n📦 모델: {model_name}")
    
    # 토큰 확인
    if HF_TOKEN:
        print(f"✅ HF_TOKEN 환경 변수 발견 (길이: {len(HF_TOKEN)})")
        os.environ['HF_TOKEN'] = HF_TOKEN
    else:
        print("⚠️  HF_TOKEN 환경 변수 없음")
        print("   토큰 없이 접근 시도 (공개 모델인 경우 가능)")
    
    # transformers 라이브러리 확인
    try:
        from transformers import AutoModelForMaskedLM, AutoTokenizer
        print("✅ transformers 라이브러리 설치됨")
    except ImportError:
        print("❌ transformers 라이브러리가 설치되지 않았습니다.")
        print("   설치: pip install transformers torch")
        return False
    
    # 모델 접근 시도
    print(f"\n🔍 모델 접근 시도 중...")
    try:
        from transformers import AutoTokenizer
        
        # 토크나이저만 먼저 시도 (가벼움)
        print("  1. 토크나이저 로드 시도...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            token=HF_TOKEN if HF_TOKEN else None
        )
        print("  ✅ 토크나이저 로드 성공!")
        
        # 간단한 테스트
        test_text = "민법 제750조 불법행위"
        tokens = tokenizer(test_text, return_tensors="pt")
        print(f"  ✅ 토큰화 테스트 성공 (토큰 수: {tokens['input_ids'].shape[1]})")
        
        # 모델 메타데이터 확인
        print("\n  2. 모델 메타데이터 확인...")
        try:
            from huggingface_hub import model_info
            info = model_info(model_name, token=HF_TOKEN if HF_TOKEN else None)
            print(f"  ✅ 모델 정보:")
            print(f"     - ID: {info.id}")
            print(f"     - 공개 여부: {info.private == False}")
            if hasattr(info, 'tags'):
                print(f"     - 태그: {', '.join(info.tags[:5])}")
        except ImportError:
            print("  ⚠️  huggingface_hub 없음 (메타데이터 확인 건너뜀)")
        except Exception as e:
            print(f"  ⚠️  메타데이터 확인 실패: {e}")
        
        # 전체 모델 로드 시도 (선택적)
        print("\n  3. 전체 모델 로드 시도 (선택적)...")
        try:
            import torch
            from transformers import AutoModelForMaskedLM
            
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"     디바이스: {device}")
            
            model = AutoModelForMaskedLM.from_pretrained(
                model_name,
                token=HF_TOKEN if HF_TOKEN else None
            )
            model.to(device)
            model.eval()
            print("  ✅ 모델 로드 성공!")
            
            # 간단한 인코딩 테스트
            print("  4. 인코딩 테스트...")
            with torch.no_grad():
                inputs = tokenizer(test_text, return_tensors="pt").to(device)
                outputs = model(**inputs)
                print(f"  ✅ 인코딩 테스트 성공 (출력 shape: {outputs.logits.shape})")
            
            print("\n" + "=" * 80)
            print("✅ HuggingFace 모델 접근 성공!")
            print("=" * 80)
            if not HF_TOKEN:
                print("\n💡 참고: 토큰 없이도 접근 가능합니다 (공개 모델).")
            return True
            
        except Exception as e:
            print(f"  ⚠️  모델 로드 실패: {e}")
            if "401" in str(e) or "Unauthorized" in str(e):
                print("\n❌ 인증 오류: 토큰이 필요합니다.")
                print("\n💡 해결 방법:")
                print("  1. HuggingFace 계정 생성: https://huggingface.co/join")
                print("  2. 토큰 생성: Settings > Access Tokens > New token")
                print("  3. .env 파일에 추가: HF_TOKEN=your_token_here")
                return False
            else:
                print(f"\n⚠️  다른 오류 발생: {e}")
                print("   토크나이저는 정상이므로 기본 기능은 사용 가능할 수 있습니다.")
                return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ 오류 발생: {error_msg}")
        
        if "401" in error_msg or "Unauthorized" in error_msg:
            print("\n❌ 인증 오류: 토큰이 필요합니다.")
            print("\n💡 해결 방법:")
            print("  1. HuggingFace 계정 생성: https://huggingface.co/join")
            print("  2. 토큰 생성: Settings > Access Tokens > New token")
            print("  3. .env 파일에 추가: HF_TOKEN=your_token_here")
            return False
        elif "404" in error_msg or "not found" in error_msg.lower():
            print("\n❌ 모델을 찾을 수 없습니다.")
            print(f"   모델명 확인: {model_name}")
            return False
        else:
            print(f"\n⚠️  예상치 못한 오류: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = check_hf_access()
    sys.exit(0 if success else 1)
