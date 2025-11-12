#!/bin/bash

# Optimized ComfyUI Startup Script for Dual Intel Xeon E5-2680 v2
# Applies all research-based CPU optimizations before launching ComfyUI

echo "Starting ComfyUI with Intel Xeon E5-2680 v2 optimizations..."

# Source optimizations
source /home/ned/ComfyUI-Install/scripts/optimize_xeon_dual.sh

# Navigate to ComfyUI directory
cd /home/ned/ComfyUI-Install/ComfyUI

# Activate virtual environment
source venv/bin/activate

# Display configuration
echo "Starting ComfyUI with the following optimizations:"
echo "- NUMA interleaving: ${NUMACTL}"
echo "- OpenMP threads: ${OMP_NUM_THREADS}"
echo "- PyTorch threads: ${TORCH_NUM_THREADS}"
echo "- Memory allocator: TCMalloc"
echo "- Huge pages: ${THP_MEM_ALLOC_ENABLE}"
echo "- Channels-last format: ${PYTORCH_CHANNELS_LAST}"

# Launch ComfyUI with NUMA-aware execution
exec ${NUMACTL} python main.py \
    --listen 0.0.0.0 \
    --port 8188 \
    --cpu \
    --fp16-vae \
    --extra-model-paths-config extra_model_paths.yaml