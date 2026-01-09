#!/bin/bash
# RunPod 인스턴스에서 SPLADE API 서버 설정 스크립트

set -e

echo "🚀 RunPod SPLADE API 서버 설정 시작"
echo ""

# 1. 작업 디렉토리 확인
if [ ! -d "/workspace/ddoksori_demo" ]; then
    echo "❌ /workspace/ddoksori_demo 디렉토리를 찾을 수 없습니다."
    echo "   프로젝트를 먼저 클론하거나 전송하세요."
    exit 1
fi

cd /workspace/ddoksori_demo

# 2. Python 환경 확인
echo "📦 Python 환경 확인 중..."
if command -v conda &> /dev/null; then
    echo "   Conda 환경 감지됨"
    if conda env list | grep -q "ddoksori"; then
        echo "   ddoksori 환경 활성화"
        source "$(conda info --base)/etc/profile.d/conda.sh"
        conda activate ddoksori
    fi
else
    echo "   Conda 없음, 시스템 Python 사용"
fi

# 3. 필수 패키지 설치
echo ""
echo "📦 필수 패키지 설치 중..."
pip install -q fastapi uvicorn sentence-transformers>=5.0.0 torch>=2.6 requests python-dotenv hf_transfer

# 4. HuggingFace 토큰 확인
echo ""
echo "🔑 HuggingFace 토큰 확인 중..."
if [ -z "$HF_TOKEN" ]; then
    if [ -f "backend/.env" ] && grep -q "HF_TOKEN" backend/.env; then
        echo "   .env 파일에서 토큰 로드"
        export $(grep HF_TOKEN backend/.env | xargs)
    else
        echo "⚠️  HF_TOKEN이 설정되지 않았습니다."
        echo "   다음 명령어로 설정하세요:"
        echo "   export HF_TOKEN=your_token_here"
        echo "   또는 backend/.env 파일에 추가하세요."
        read -p "   계속하시겠습니까? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    echo "   ✅ HF_TOKEN 설정됨"
fi

# 5. API 서버 파일 확인
echo ""
echo "📄 API 서버 파일 확인 중..."
if [ ! -f "backend/runpod_splade_server.py" ]; then
    echo "❌ backend/runpod_splade_server.py 파일을 찾을 수 없습니다."
    exit 1
fi
echo "   ✅ 파일 확인됨"

# 6. CUDA 확인
echo ""
echo "🎮 GPU 확인 중..."
python3 -c "import torch; print(f'   CUDA available: {torch.cuda.is_available()}'); print(f'   Device count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}')" || echo "   ⚠️  torch 확인 실패"

# 7. 서버 실행 안내
echo ""
echo "✅ 설정 완료!"
echo ""
echo "다음 명령어로 서버를 실행하세요:"
echo ""
echo "  cd /workspace/ddoksori_demo/backend"
echo "  uvicorn runpod_splade_server:app --host 0.0.0.0 --port 8000"
echo ""
echo "또는 백그라운드 실행:"
echo ""
echo "  nohup uvicorn runpod_splade_server:app --host 0.0.0.0 --port 8000 > splade_server.log 2>&1 &"
echo ""
