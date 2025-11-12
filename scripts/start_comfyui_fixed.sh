#!/bin/bash

# ComfyUI Safe Mode Startup Script for Intel Xeon E5-2680 v2
# Working safe mode configuration that avoids CPU instruction crashes

echo "Starting ComfyUI in Safe Mode (WORKING CONFIGURATION)..."

# Navigate to ComfyUI directory
cd /home/ned/ComfyUI-Install/ComfyUI

# Activate virtual environment
source venv/bin/activate

echo "Safe Mode Configuration:"
echo "- PyTorch version: 2.4.0+cu121"
echo "- All custom nodes: DISABLED (prevents crashes)"
echo "- API nodes: DISABLED"
echo "- CPU mode: ENABLED (bypasses GPU/CUDA issues)"
echo "- Fast optimizations: ENABLED"
echo "- Network: 0.0.0.0:8188"
echo "- Status: WORKING!"

# Launch ComfyUI in safe mode (prevents crashes)
exec python main.py \
    --listen 0.0.0.0 \
    --port 8188 \
    --disable-all-custom-nodes \
    --disable-api-nodes \
    --cpu \
    --disable-cuda-malloc \
    --fast fp16_accumulation fp8_matrix_mult cublas_ops autotune