#!/bin/bash
# RunPod  SPLADE API   

set -e

echo " RunPod SPLADE API   "
echo ""

# 1.   
if [ ! -d "/workspace/ddoksori_demo" ]; then
    echo " /workspace/ddoksori_demo    ."
    echo "      ."
    exit 1
fi

cd /workspace/ddoksori_demo

# 2. Python  
echo " Python   ..."
if command -v conda &> /dev/null; then
    echo "   Conda  "
    if conda env list | grep -q "ddoksori"; then
        echo "   ddoksori  "
        source "$(conda info --base)/etc/profile.d/conda.sh"
        conda activate ddoksori
    fi
else
    echo "   Conda ,  Python "
fi

# 3.   
echo ""
echo "    ..."
pip install -q fastapi uvicorn sentence-transformers>=5.0.0 torch>=2.6 requests python-dotenv hf_transfer

# 4. HuggingFace  
echo ""
echo " HuggingFace   ..."
if [ -z "$HF_TOKEN" ]; then
    if [ -f "backend/.env" ] && grep -q "HF_TOKEN" backend/.env; then
        echo "   .env   "
        export $(grep HF_TOKEN backend/.env | xargs)
    else
        echo "  HF_TOKEN  ."
        echo "     :"
        echo "   export HF_TOKEN=your_token_here"
        echo "    backend/.env  ."
        read -p "   ? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    echo "    HF_TOKEN "
fi

# 5. API   
echo ""
echo " API    ..."
if [ ! -f "backend/runpod_splade_server.py" ]; then
    echo " backend/runpod_splade_server.py    ."
    exit 1
fi
echo "     "

# 6. CUDA 
echo ""
echo " GPU  ..."
python3 -c "import torch; print(f'   CUDA available: {torch.cuda.is_available()}'); print(f'   Device count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}')" || echo "     torch  "

# 7.   
echo ""
echo "  !"
echo ""
echo "   :"
echo ""
echo "  cd /workspace/ddoksori_demo/backend"
echo "  uvicorn runpod_splade_server:app --host 0.0.0.0 --port 8000"
echo ""
echo "  :"
echo ""
echo "  nohup uvicorn runpod_splade_server:app --host 0.0.0.0 --port 8000 > splade_server.log 2>&1 &"
echo ""
