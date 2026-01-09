#!/bin/bash
# RunPod에서 torch 업그레이드 스크립트
# 사용법: RunPod 인스턴스에 SSH 접속 후 실행

echo "=========================================="
echo "RunPod torch 업그레이드 스크립트"
echo "=========================================="

# 1. 현재 상태 확인
echo ""
echo "1️⃣ 현재 상태 확인..."
python3 -c "import torch; print(f'torch 버전: {torch.__version__}'); print(f'CUDA 버전: {torch.version.cuda}'); print(f'CUDA 사용 가능: {torch.cuda.is_available()}')"

# 2. CUDA 버전 확인
CUDA_VERSION=$(python3 -c "import torch; print(torch.version.cuda)" 2>/dev/null | cut -d'.' -f1,2)
echo ""
echo "2️⃣ CUDA 버전: $CUDA_VERSION"

# 3. torch 업그레이드
echo ""
echo "3️⃣ torch 업그레이드 중..."
echo "   CUDA $CUDA_VERSION에 맞는 torch 2.6 이상 설치..."

if [[ "$CUDA_VERSION" == "12.4" ]]; then
    pip install --upgrade torch>=2.6 --index-url https://download.pytorch.org/whl/cu124
elif [[ "$CUDA_VERSION" == "12.1" ]]; then
    pip install --upgrade torch>=2.6 --index-url https://download.pytorch.org/whl/cu121
elif [[ "$CUDA_VERSION" == "11.8" ]]; then
    pip install --upgrade torch>=2.6 --index-url https://download.pytorch.org/whl/cu118
else
    echo "   ⚠️  CUDA 버전을 자동 감지하지 못했습니다. 기본 설치를 시도합니다..."
    pip install --upgrade torch>=2.6
fi

# 4. 업그레이드 확인
echo ""
echo "4️⃣ 업그레이드 확인..."
python3 -c "import torch; print(f'✅ torch 버전: {torch.__version__}'); print(f'✅ CUDA 사용 가능: {torch.cuda.is_available()}')"

# 5. 버전 체크
TORCH_VERSION=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null)
MAJOR=$(echo $TORCH_VERSION | cut -d'.' -f1)
MINOR=$(echo $TORCH_VERSION | cut -d'.' -f2)

if [ "$MAJOR" -gt 2 ] || ([ "$MAJOR" -eq 2 ] && [ "$MINOR" -ge 6 ]); then
    echo ""
    echo "✅ torch 버전이 2.6 이상입니다!"
    echo ""
    echo "다음 단계:"
    echo "  cd /workspace/ddoksori_demo/backend"
    echo "  uvicorn runpod_splade_server:app --host 0.0.0.0 --port 8000"
else
    echo ""
    echo "❌ torch 버전이 여전히 2.6 미만입니다."
    echo "   수동으로 업그레이드하세요:"
    echo "   pip install --upgrade torch>=2.6 --index-url https://download.pytorch.org/whl/cu124"
fi
