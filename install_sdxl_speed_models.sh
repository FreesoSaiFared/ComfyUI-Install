#!/bin/bash

# SDXL Speed Models Installation Script
# Installs Hyper SDXL and SDXL Lightning models for fast generation

set -e

COMFYUI_DIR="/home/ned/ComfyUI-Install/ComfyUI"
MODELS_DIR="$COMFYUI_DIR/models"
CHECKPOINTS_DIR="$MODELS_DIR/checkpoints"
UNET_DIR="$MODELS_DIR/unet"

echo "🚀 SDXL Speed Models Installation Script"
echo "========================================="
echo "ComfyUI Directory: $COMFYUI_DIR"
echo "Checkpoints Dir: $CHECKPOINTS_DIR"
echo "UNET Dir: $UNET_DIR"
echo

# Create directories if they don't exist
mkdir -p "$CHECKPOINTS_DIR"
mkdir -p "$UNET_DIR"

# Function to check if model exists
model_exists() {
    local model_path="$1"
    local model_name=$(basename "$model_path")

    if [ -f "$model_path" ]; then
        local size=$(stat -f%z "$model_path" 2>/dev/null || stat -c%s "$model_path" 2>/dev/null || echo "0")
        echo "✅ $model_name exists ($(numfmt --to=iec $size))"
        return 0
    else
        echo "❌ $model_name missing"
        return 1
    fi
}

# Function to download with progress and verification
download_model() {
    local url="$1"
    local output_path="$2"
    local model_name=$(basename "$output_path")
    local expected_size="$3"  # in bytes

    if model_exists "$output_path"; then
        echo "✅ $model_name already exists, skipping download"
        return 0
    fi

    echo "📥 Downloading $model_name..."
    echo "   URL: $url"
    echo "   Output: $output_path"
    echo "   Size: $expected_size"

    # Use aria2c for better downloading of large files
    if command -v aria2c >/dev/null 2>&1; then
        echo "   Using aria2c for faster download..."
        aria2c -x 16 -s 16 --max-tries=5 --retry-wait=10 \
               --file-allocation=none \
               --max-file-not-found=5 \
               --summary-interval=60 \
               --show-console-readout=true \
               --check-integrity=true \
               -d "$(dirname "$output_path")" \
               -o "$(basename "$output_path")" \
               "$url"
    else
        echo "   Using wget..."
        wget --continue --timeout=300 --tries=5 --retry-connrefused \
             --progress=bar:force \
             -O "$output_path" \
             "$url"
    fi

    # Verify download
    if model_exists "$output_path"; then
        echo "✅ $model_name downloaded successfully!"
        return 0
    else
        echo "❌ Failed to download $model_name"
        return 1
    fi
}

echo "📋 Checking Required Components..."
echo "================================"

# 1. Check if custom node is installed
if [ -d "$COMFYUI_DIR/custom_nodes/ComfyUI-HyperSDXL1StepUnetScheduler" ]; then
    echo "✅ HyperSDXL 1-Step UNet Scheduler custom node is installed"
else
    echo "❌ HyperSDXL 1-Step UNet Scheduler custom node missing"
    echo "   Installing..."
    cd "$COMFYUI_DIR/custom_nodes"
    git clone https://github.com/fofr/ComfyUI-HyperSDXL1StepUnetScheduler.git
    echo "✅ HyperSDXL custom node installed"
fi

echo
echo "📥 Installing SDXL Lightning Models (High Priority)..."
echo "============================================================"

# SDXL Lightning 4-Step Models (smaller and more flexible)
echo "Installing SDXL Lightning 4-step UNet (recommended)..."
download_model "https://huggingface.co/ByteDance/SDXL-Lightning/resolve/main/sdxl_lightning_4step_unet.safetensors" \
             "$UNET_DIR/sdxl_lightning_4step_unet.safetensors" \
             "5135149736"

echo
echo "📥 Installing SDXL Lightning 4-Step Full Checkpoint (optional)..."
echo "=============================================================="
echo "⚠️  This is a large 6.5GB download - may take a while..."
read -p "Continue with full checkpoint download? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    download_model "https://huggingface.co/ByteDance/SDXL-Lightning/resolve/main/sdxl_lightning_4step.safetensors" \
                 "$CHECKPOINTS_DIR/sdxl_lightning_4step.safetensors" \
                 "6938040682"
else
    echo "⏭️  Skipping full checkpoint download (UNet-only is sufficient)"
fi

echo
echo "📥 Installing Hyper SDXL 1-Step Model (Advanced)..."
echo "=================================================="
echo "⚠️  This is a very large 6.5GB download for 1-step generation"
read -p "Continue with Hyper SDXL 1-Step download? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    download_model "https://huggingface.co/ByteDance/Hyper-SD/resolve/main/Hyper-SDXL-1step-Unet-Comfyui.fp16.safetensors" \
                 "$CHECKPOINTS_DIR/Hyper-SDXL-1step-Unet-Comfyui.fp16.safetensors" \
                 "6938040294"
else
    echo "⏭️  Skipping Hyper SDXL download"
fi

echo
echo "📊 Installation Summary..."
echo "======================="

# Check what we have installed
echo "✅ Custom Nodes:"
echo "   - ComfyUI-HyperSDXL1StepUnetScheduler: $(if [ -d "$COMFYUI_DIR/custom_nodes/ComfyUI-HyperSDXL1StepUnetScheduler" ]; then echo "INSTALLED"; else echo "MISSING"; fi)"

echo
echo "✅ Models Installed:"
echo "   Checkpoints:"
for model in "$CHECKPOINTS_DIR"/*.safetensors; do
    if [ -f "$model" ]; then
        size=$(stat -f%z "$model" 2>/dev/null || stat -c%s "$model" 2>/dev/null || echo "0")
        name=$(basename "$model")
        echo "   - $name ($(numfmt --to=iec $size))"
    fi
done

echo "   UNet:"
for model in "$UNET_DIR"/*.safetensors; do
    if [ -f "$model" ]; then
        size=$(stat -f%z "$model" 2>/dev/null || stat -c%s "$model" 2>/dev/null || echo "0")
        name=$(basename "$model")
        echo "   - $name ($(numfmt --to=iec $size))"
    fi
done

echo
echo "📋 Usage Instructions..."
echo "====================="

echo "SDXL Lightning 4-Step (Recommended):"
echo "------------------------------------"
echo "1. Load your base SDXL 1.0 model with 'Load Checkpoint'"
echo "2. Add a 'Load UNET' node and load sdxl_lightning_4step_unet.safetensors"
echo "3. Connect the UNET to your sampler"
echo "4. Use KSampler with these settings:"
echo "   - steps: 4"
echo "   - cfg: 1.0"
echo "   - sampler_name: dpmpp_2m_sde or euler"
echo "   - scheduler: sgm_uniform or karras"

if [ -f "$CHECKPOINTS_DIR/sdxl_lightning_4step.safetensors" ]; then
echo
echo "OR use the full checkpoint:"
echo "1. Load sdxl_lightning_4step.safetensors with 'Load Checkpoint'"
echo "2. Same KSampler settings as above"
fi

if [ -f "$CHECKPOINTS_DIR/Hyper-SDXL-1step-Unet-Comfyui.fp16.safetensors" ]; then
echo
echo "Hyper SDXL 1-Step (Advanced):"
echo "----------------------------"
echo "1. Load Hyper-SDXL-1step-Unet-Comfyui.fp16.safetensors"
echo "2. Use SamplerCustom with Hyper SDXL 1-Step UNET node"
echo "3. steps: 1, cfg: 1.0"
echo "4. Requires the HyperSDXL 1-Step UNET Scheduler node"
fi

echo
echo "🔄 ComfyUI Restart Needed..."
echo "============================"
echo "The new custom node requires ComfyUI to be restarted."

read -p "Restart ComfyUI now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 Restarting ComfyUI..."
    cd "$COMFYUI_DIR"

    # Stop any running ComfyUI processes
    pkill -f "python.*main.py" || true

    # Wait a moment
    sleep 2

    # Start ComfyUI with the RTX 3060 optimized settings
    source venv/bin/activate && python main.py --listen 0.0.0.0 --port 8188 --cpu &

    echo "✅ ComfyUI restarted with new speed models!"
    echo "🌐 Access at: http://192.168.178.15:8188"
else
    echo "⚠️  Remember to restart ComfyUI to load the new custom node"
fi

echo
echo "🎉 Installation Complete!"