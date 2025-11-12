#!/usr/bin/env bash
set -euo pipefail

echo "=== Downloading Wan2.1 Fun-Control Models ==="
echo "This will download ~15GB of models"
echo

# Create directories
mkdir -p models/diffusion_models
mkdir -p models/text_encoders
mkdir -p models/vae
mkdir -p models/clip_vision

# Download 1.3B Fun-Control Model
echo "Downloading Wan2.1-Fun-1.3B-Control (10.5GB)..."
wget -c --show-progress -O models/diffusion_models/Wan2.1-Fun-1.3B-Control.safetensors \
  "https://huggingface.co/alibaba-pai/Wan2.1-Fun-1.3B-Control/resolve/main/diffusion_pytorch_model.safetensors"

# Download Text Encoder (fp8 version - more efficient)
echo "Downloading Text Encoder (fp8)..."
wget -c --show-progress -O models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"

# Download Text Encoder (fp16 version - alternative)
echo "Downloading Text Encoder (fp16)..."
wget -c --show-progress -O models/text_encoders/umt5_xxl_fp16.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp16.safetensors"

# Download VAE
echo "Downloading VAE..."
wget -c --show-progress -O models/vae/wan_2.1_vae.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors"

# Download CLIP Vision
echo "Downloading CLIP Vision..."
wget -c --show-progress -O models/clip_vision/clip_vision_h.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors"

# Optional: 14B fp8 model (much larger)
echo "Optional: Downloading 14B fp8 model (6.4GB)..."
wget -c --show-progress -O models/diffusion_models/Wan2.1-Fun-Control-14B_fp8_e4m3fn.safetensors \
  "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2.1-Fun-Control-14B_fp8_e4m3fn.safetensors"

echo
echo "=== Download Complete! ==="
echo "Models are now available in:"
echo "- Diffusion models: models/diffusion_models/"
echo "- Text encoders: models/text_encoders/"
echo "- VAE: models/vae/"
echo "- CLIP Vision: models/clip_vision/"
echo
echo "Restart ComfyUI to see the models in the interface."