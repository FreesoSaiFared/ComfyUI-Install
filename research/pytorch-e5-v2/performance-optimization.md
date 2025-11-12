# Performance Optimization Guide: PyTorch on Intel Xeon E5 v2 + RTX 3060

## Overview

This guide provides comprehensive optimization strategies for running PyTorch on Intel Xeon E5 v2 processors with RTX 3060 GPUs. The focus is on maximizing performance while working around the CPU's instruction set limitations (no AVX2/AVX512).

## 1. Hardware Bottleneck Analysis

### Performance Profile
```
[CPU] Intel Xeon E5 v2 (AVX only)     ← Bottleneck
  ↑
[GPU] RTX 3060 12GB (Ampere)         ← Highly capable
```

### Bottleneck Identification
```python
import torch
import time

def profile_operations():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Test CPU operations
    start = time.time()
    x_cpu = torch.randn(10000, 10000)
    y_cpu = torch.mm(x_cpu, x_cpu.t())
    cpu_time = time.time() - start

    # Test GPU operations
    if torch.cuda.is_available():
        start = time.time()
        x_gpu = torch.randn(10000, 10000, device='cuda')
        y_gpu = torch.mm(x_gpu, x_gpu.t())
        torch.cuda.synchronize()
        gpu_time = time.time() - start

        print(f"CPU Time: {cpu_time:.3f}s")
        print(f"GPU Time: {gpu_time:.3f}s")
        print(f"GPU Speedup: {cpu_time/gpu_time:.1f}x")

profile_operations()
```

## 2. Memory Optimization Strategies

### 2.1 Memory Management
```python
# Pin memory for faster CPU-GPU transfers
dataloader = DataLoader(
    dataset,
    batch_size=32,
    num_workers=4,
    pin_memory=True,  # Critical for performance
    persistent_workers=True
)

# Optimize memory allocation
torch.cuda.empty_cache()  # Clear unused memory
torch.backends.cudnn.benchmark = True  # Optimize for consistent input sizes

# Memory-efficient training
with torch.cuda.amp.autocast():  # Mixed precision
    outputs = model(inputs)
    loss = criterion(outputs, targets)

# Gradient checkpointing for memory-intensive models
from torch.utils.checkpoint import checkpoint
output = checkpoint(expensive_function, input_tensor)
```

### 2.2 Batch Size Optimization
```python
def find_optimal_batch_size(model, dataloader, device):
    """Find the largest batch size that fits in GPU memory"""
    batch_sizes = [8, 16, 32, 48, 64, 96, 128]
    optimal_size = 8

    for batch_size in batch_sizes:
        try:
            # Test with dummy data
            dummy_input = torch.randn(batch_size, 3, 224, 224, device=device)
            dummy_output = model(dummy_input)
            del dummy_input, dummy_output
            torch.cuda.empty_cache()
            optimal_size = batch_size
        except RuntimeError as e:
            if "out of memory" in str(e):
                break
            else:
                raise e

    return optimal_size
```

## 3. Data Loading Optimization

### 3.1 Parallel Data Loading
```python
# Optimized DataLoader for legacy CPU
dataloader = DataLoader(
    dataset,
    batch_size=32,
    shuffle=True,
    num_workers=min(8, os.cpu_count()),  # Adjust based on your CPU cores
    pin_memory=True,
    persistent_workers=True,  # Keep workers alive
    prefetch_factor=2,  # Prefetch batches
    drop_last=True  # Consistent batch sizes
)
```

### 3.2 Custom Dataset Optimization
```python
import cv2
import numpy as np
from torch.utils.data import Dataset

class OptimizedDataset(Dataset):
    def __init__(self, image_paths, labels, transform=None):
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform
        self.cache = {}  # Simple LRU cache

    def __getitem__(self, idx):
        # Check cache first
        if idx in self.cache:
            image = self.cache[idx]
        else:
            # Use OpenCV for faster image loading
            image = cv2.imread(self.image_paths[idx])
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Cache if not too large
            if len(self.cache) < 1000:
                self.cache[idx] = image

        if self.transform:
            image = self.transform(image)

        return image, self.labels[idx]
```

## 4. Model Optimization

### 4.1 Model Architecture Selection
```python
# Models that work well with CPU bottlenecks
CPU_FRIENDLY_MODELS = {
    'efficientnet_b0': 'Good balance of accuracy and speed',
    'mobilenet_v2': 'Very efficient for inference',
    'resnet18': 'Classic, well-optimized',
    'squeezenet1_0': 'Very lightweight'
}

# Models to avoid on CPU-limited systems
CPU_HEAVY_MODELS = {
    'vision_transformer': 'Heavy attention computations',
    'swin_transformer': 'Complex window operations',
    'convnext_base': 'Large convolutions'
}
```

### 4.2 Quantization
```python
# Post-training quantization for inference
import torch.quantization

def quantize_model(model, dataloader):
    # Prepare model for quantization
    model.eval()
    model.qconfig = torch.quantization.get_default_qconfig('fbgemm')
    torch.quantization.prepare(model, inplace=True)

    # Calibrate with sample data
    with torch.no_grad():
        for data, _ in dataloader:
            model(data)
            break  # Just need calibration data

    # Convert to quantized model
    quantized_model = torch.quantization.convert(model, inplace=False)
    return quantized_model

# Usage
quantized_model = quantize_model(model, calibration_dataloader)
```

## 5. Training Optimization

### 5.1 Mixed Precision Training
```python
# Automatic Mixed Precision (AMP)
from torch.cuda.amp import autocast, GradScaler

def train_with_amp(model, dataloader, optimizer, criterion, device):
    scaler = GradScaler()
    model.train()

    for batch_idx, (data, target) in enumerate(dataloader):
        data, target = data.to(device), target.to(device)

        optimizer.zero_grad()

        # Forward pass with autocast
        with autocast():
            output = model(data)
            loss = criterion(output, target)

        # Backward pass with gradient scaling
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
```

### 5.2 Gradient Accumulation
```python
def train_with_gradient_accumulation(
    model, dataloader, optimizer, criterion, device,
    accumulation_steps=4, effective_batch_size=128
):
    model.train()
    optimizer.zero_grad()

    for batch_idx, (data, target) in enumerate(dataloader):
        data, target = data.to(device), target.to(device)

        # Forward pass
        with autocast():
            output = model(data)
            loss = criterion(output, target)
            loss = loss / accumulation_steps

        # Backward pass
        scaler.scale(loss).backward()

        # Update weights every accumulation_steps
        if (batch_idx + 1) % accumulation_steps == 0:
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad()
```

## 6. Runtime Optimization

### 6.1 Threading and Parallelization
```python
import torch
import os

# Optimize threading for legacy CPU
def optimize_threading():
    # Set number of threads for PyTorch operations
    num_threads = min(os.cpu_count(), 8)  # Don't oversubscribe
    torch.set_num_threads(num_threads)

    # Set inter-op parallelism
    torch.set_num_interop_threads(2)

    # Environment variables
    os.environ['OMP_NUM_THREADS'] = str(num_threads)
    os.environ['MKL_NUM_THREADS'] = str(num_threads)
    os.environ['NUMEXPR_NUM_THREADS'] = str(num_threads)

# Apply optimizations
optimize_threading()
```

### 6.2 Environment Variables
```bash
# Add to your environment or script
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
export KMP_AFFINITY=granularity=fine,compact,1,0
export KMP_BLOCKTIME=1
export CUDA_LAUNCH_BLOCKING=0  # Async execution
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
```

## 7. Monitoring and Profiling

### 7.1 Performance Monitoring
```python
import time
import psutil
import torch

class PerformanceMonitor:
    def __init__(self):
        self.start_time = None
        self.measurements = []

    def start(self):
        self.start_time = time.time()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

    def measure(self, name):
        current_time = time.time()
        cpu_percent = psutil.cpu_percent()
        memory_mb = psutil.virtual_memory().used / (1024 * 1024)

        measurement = {
            'name': name,
            'time': current_time - self.start_time,
            'cpu_percent': cpu_percent,
            'memory_mb': memory_mb
        }

        if torch.cuda.is_available():
            measurement['gpu_memory_mb'] = torch.cuda.memory_allocated() / (1024 * 1024)
            measurement['gpu_utilization'] = torch.cuda.utilization()

        self.measurements.append(measurement)
        return measurement

# Usage
monitor = PerformanceMonitor()
monitor.start()

# During training
output = model(input)
epoch_stats = monitor.measure('forward_pass')
```

### 7.2 Profiling CPU vs GPU Performance
```python
import torch.profiler

def profile_model_performance(model, dataloader, device):
    """Profile model performance to identify bottlenecks"""

    with torch.profiler.profile(
        activities=[
            torch.profiler.ProfilerActivity.CPU,
            torch.profiler.ProfilerActivity.CUDA,
        ],
        schedule=torch.profiler.schedule(
            wait=1, warmup=1, active=3, repeat=2
        ),
        on_trace_ready=torch.profiler.tensorboard_trace_handler('./logs'),
        record_shapes=True,
        profile_memory=True,
        with_stack=True
    ) as prof:

        for batch_idx, (data, target) in enumerate(dataloader):
            if batch_idx >= 10:  # Profile first 10 batches
                break

            data, target = data.to(device), target.to(device)

            with torch.profiler.record_function("model_inference"):
                output = model(data)

            prof.step()

    # Print summary
    print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=10))
```

## 8. Specific Optimizations for Common Tasks

### 8.1 Image Classification
```python
# Optimized image classification pipeline
def create_optimized_classification_pipeline(model, num_classes=1000):
    # Use efficient transforms
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                           std=[0.229, 0.224, 0.225])
    ])

    # Enable model optimizations
    model.eval()

    # Fuse consecutive operations where possible
    if hasattr(model, 'fuse_modules'):
        model.fuse_modules()

    return model, transform
```

### 8.2 Natural Language Processing
```python
# Optimized NLP pipeline
def optimize_nlp_model(model, tokenizer, max_length=512):
    # Enable attention optimizations
    if hasattr(model.config, 'use_cache'):
        model.config.use_cache = True

    # Use gradient checkpointing for memory efficiency
    if hasattr(model, 'gradient_checkpointing_enable'):
        model.gradient_checkpointing_enable()

    # Optimize for inference
    model.eval()

    return model, tokenizer
```

## 9. Performance Benchmarks

### Expected Performance Metrics

| Operation | Target Performance | Acceptable Range |
|-----------|-------------------|------------------|
| Image Classification (ResNet-18) | <15ms | 10-25ms |
| Object Detection (YOLOv5s) | <25ms | 20-40ms |
| Text Generation (GPT-2 Small) | <30ms | 25-50ms |
| Data Loading | <5ms/batch | 3-10ms/batch |
| GPU Utilization | >80% | 70-90% |
| CPU Utilization | 60-80% | 50-90% |

### Benchmarking Script
```python
import torch
import time
import numpy as np

def benchmark_pytorch_setup(device='cuda'):
    """Comprehensive benchmark for PyTorch setup"""

    results = {}

    # 1. Matrix multiplication benchmark
    sizes = [512, 1024, 2048]
    for size in sizes:
        x = torch.randn(size, size, device=device)

        start = time.time()
        for _ in range(100):
            y = torch.mm(x, x.t())
        if device == 'cuda':
            torch.cuda.synchronize()

        results[f'matmul_{size}'] = (time.time() - start) / 100

    # 2. Convolution benchmark
    conv = torch.nn.Conv2d(3, 64, 3).to(device)
    input_tensor = torch.randn(32, 3, 224, 224, device=device)

    start = time.time()
    for _ in range(100):
        output = conv(input_tensor)
    if device == 'cuda':
        torch.cuda.synchronize()

    results['convolution'] = (time.time() - start) / 100

    # 3. Memory bandwidth test
    data = torch.randn(1000000, device=device)

    start = time.time()
    for _ in range(100):
        y = data * 2
    if device == 'cuda':
        torch.cuda.synchronize()

    results['memory_bandwidth'] = (time.time() - start) / 100

    return results

# Run benchmarks
if torch.cuda.is_available():
    print("GPU Benchmarks:")
    gpu_results = benchmark_pytorch_setup('cuda')
    for k, v in gpu_results.items():
        print(f"  {k}: {v*1000:.2f}ms")

print("\nCPU Benchmarks:")
cpu_results = benchmark_pytorch_setup('cpu')
for k, v in cpu_results.items():
    print(f"  {k}: {v*1000:.2f}ms")
```

## 10. Troubleshooting Performance Issues

### Common Performance Problems and Solutions

| Problem | Diagnosis | Solution |
|---------|-----------|----------|
| Slow data loading | CPU bottleneck in data preprocessing | Increase num_workers, use pin_memory, optimize transforms |
| GPU underutilization | Data transfer bottleneck | Increase batch size, use pin_memory, prefetch data |
| Out of memory errors | Excessive memory usage | Use gradient checkpointing, reduce batch size, enable mixed precision |
| Slow training | CPU not keeping up with GPU | Optimize data loading, use smaller models, enable gradient accumulation |
| Inconsistent performance | Variable input sizes | Use consistent input sizes, enable cudnn.benchmark |

This optimization guide provides comprehensive strategies for maximizing PyTorch performance on Intel Xeon E5 v2 processors with RTX 3060 GPUs.