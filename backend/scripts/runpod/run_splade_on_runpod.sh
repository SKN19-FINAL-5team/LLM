#!/bin/bash
# RunPod SPLADE   
# : RunPod  SSH   

echo "=========================================="
echo "SPLADE   (RunPod GPU)"
echo "=========================================="

# CUDA 
echo " CUDA  ..."
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}'); print(f'Device name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

#    (RunPod   )
# : cd /workspace/ddoksori_demo   
# cd /workspace/ddoksori_demo

# Conda   ( )
# conda activate ddoksori

#   
echo ""
echo " SPLADE  ..."
cd backend/scripts
python evaluate_splade_poc.py

echo ""
echo "  !"
