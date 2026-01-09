#!/bin/bash
# RunPod torch  
# : RunPod  SSH   

echo "=========================================="
echo "RunPod torch  "
echo "=========================================="

# 1.   
echo ""
echo "1⃣   ..."
python3 -c "import torch; print(f'torch : {torch.__version__}'); print(f'CUDA : {torch.version.cuda}'); print(f'CUDA  : {torch.cuda.is_available()}')"

# 2. CUDA  
CUDA_VERSION=$(python3 -c "import torch; print(torch.version.cuda)" 2>/dev/null | cut -d'.' -f1,2)
echo ""
echo "2⃣ CUDA : $CUDA_VERSION"

# 3. torch 
echo ""
echo "3⃣ torch  ..."
echo "   CUDA $CUDA_VERSION  torch 2.6  ..."

if [[ "$CUDA_VERSION" == "12.4" ]]; then
    pip install --upgrade torch>=2.6 --index-url https://download.pytorch.org/whl/cu124
elif [[ "$CUDA_VERSION" == "12.1" ]]; then
    pip install --upgrade torch>=2.6 --index-url https://download.pytorch.org/whl/cu121
elif [[ "$CUDA_VERSION" == "11.8" ]]; then
    pip install --upgrade torch>=2.6 --index-url https://download.pytorch.org/whl/cu118
else
    echo "     CUDA    .   ..."
    pip install --upgrade torch>=2.6
fi

# 4.  
echo ""
echo "4⃣  ..."
python3 -c "import torch; print(f' torch : {torch.__version__}'); print(f' CUDA  : {torch.cuda.is_available()}')"

# 5.  
TORCH_VERSION=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null)
MAJOR=$(echo $TORCH_VERSION | cut -d'.' -f1)
MINOR=$(echo $TORCH_VERSION | cut -d'.' -f2)

if [ "$MAJOR" -gt 2 ] || ([ "$MAJOR" -eq 2 ] && [ "$MINOR" -ge 6 ]); then
    echo ""
    echo " torch  2.6 !"
    echo ""
    echo " :"
    echo "  cd /workspace/ddoksori_demo/backend"
    echo "  uvicorn runpod_splade_server:app --host 0.0.0.0 --port 8000"
else
    echo ""
    echo " torch   2.6 ."
    echo "    :"
    echo "   pip install --upgrade torch>=2.6 --index-url https://download.pytorch.org/whl/cu124"
fi
