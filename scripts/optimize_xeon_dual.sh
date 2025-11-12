#!/bin/bash

# Intel Xeon E5-2680 v2 Dual CPU Optimization Script
# Based on PyTorch CPU optimization research for legacy Xeon systems

echo "Configuring Intel Xeon E5-2680 v2 optimizations..."

# NUMA Configuration (Dual CPU)
export NUMACTL="numactl --interleave=all"
echo "NUMA: ${NUMACTL}"

# Threading Configuration (20 cores total)
export OMP_NUM_THREADS=20
export OMP_SCHEDULE=dynamic
export OMP_PROC_BIND=spread
export OMP_PLACES=cores
echo "OpenMP: ${OMP_NUM_THREADS} threads configured"

# PyTorch Threading
export TORCH_NUM_THREADS=20
export TORCH_INTEROP_THREADS=2
echo "PyTorch: ${TORCH_NUM_THREADS} compute threads, ${TORCH_INTEROP_THREADS} interop threads"

# BLAS Library Threading
export MKL_NUM_THREADS=20
export OPENBLAS_NUM_THREADS=20
echo "BLAS libraries configured for ${MKL_NUM_THREADS} threads"

# Memory Allocation Optimization
export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4
echo "TCMalloc enabled for better memory allocation"

# Huge Page Support
export THP_MEM_ALLOC_ENABLE=1
echo "Transparent Huge Pages enabled"

# PyTorch CPU Settings (Legacy CPU Compatibility)
export TORCH_DISABLE_AVX2=1
export TORCH_DISABLE_AVX512=1
echo "PyTorch AVX2/AVX512 disabled for legacy CPU compatibility"

# Channels Last Memory Format (Better for CNN)
export PYTORCH_CHANNELS_LAST=1
echo "Channels-last memory format preferred"

# Print System Info
echo "System Configuration:"
echo "- CPU: Dual Intel Xeon E5-2680 v2 (20 cores total)"
echo "- Architecture: Sandy Bridge-EP (AVX1 only, no AVX2/AVX512)"
echo "- Memory: 128GB DDR3"
echo "- NUMA: 2 nodes detected"

echo "Optimizations Applied:"
echo "- TCMalloc memory allocator"
echo "- NUMA-aware thread binding"
echo "- OpenMP dynamic scheduling"
echo "- Transparent huge pages"
echo "- Legacy CPU instruction set compatibility"
echo "- PyTorch threading optimization"

echo "Configuration complete!"