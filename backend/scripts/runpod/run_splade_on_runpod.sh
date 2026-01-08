#!/bin/bash
# RunPod에서 SPLADE 평가 실행 스크립트
# 사용법: RunPod 인스턴스에 SSH 접속 후 실행

echo "=========================================="
echo "SPLADE 평가 스크립트 (RunPod GPU)"
echo "=========================================="

# CUDA 확인
echo "🔍 CUDA 상태 확인..."
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}'); print(f'Device name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

# 프로젝트 디렉토리로 이동 (RunPod에서 프로젝트가 있는 위치)
# 예: cd /workspace/ddoksori_demo 또는 적절한 경로
# cd /workspace/ddoksori_demo

# Conda 환경 활성화 (필요한 경우)
# conda activate ddoksori

# 평가 스크립트 실행
echo ""
echo "🚀 SPLADE 평가 시작..."
cd backend/scripts
python evaluate_splade_poc.py

echo ""
echo "✅ 평가 완료!"
