#!/bin/bash

# Legacy CPU Compatibility Script for Intel Xeon E5-2680 v2
# Maximum compatibility mode avoiding modern CPU instruction crashes

echo "Starting ComfyUI in Legacy CPU Compatibility Mode..."

# Basic NUMA and Threading (Conservative Settings)
export OMP_NUM_THREADS=8
export OMP_PROC_BIND=close
export OMP_PLACES=cores
export TORCH_NUM_THREADS=8
export MKL_NUM_THREADS=8
export OPENBLAS_NUM_THREADS=8

# Memory Allocator
export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4

# CPU Compatibility Flags
export TORCH_DISABLE_AVX2=1
export TORCH_DISABLE_AVX512=1

# Disable Advanced Features (May cause crashes on legacy CPUs)
export TORCH_ENABLE_CPU_FALLBACK=1
export CUDA_VISIBLE_DEVICES=""

# Navigate to ComfyUI directory
cd /home/ned/ComfyUI-Install/ComfyUI

# Activate virtual environment
source venv/bin/activate

echo "Legacy Configuration:"
echo "- Conservative threading: ${OMP_NUM_THREADS} threads"
echo "- Memory allocator: TCMalloc"
echo "- AVX2/AVX512: Disabled"
echo "- Advanced features: Disabled for compatibility"

# Launch ComfyUI with conservative settings
exec numactl --cpunodebind=0 --membind=0 python main.py \
    --listen 0.0.0.0 \
    --port 8188 \
    --cpu \
    --fp16-vae \
    --extra-model-paths-config extra_model_paths.yaml \
    --disable-cuda-malloc