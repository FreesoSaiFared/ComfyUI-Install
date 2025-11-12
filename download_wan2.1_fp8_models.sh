#!/usr/bin/env bash
set -euo pipefail

echo "=== Downloading Wan2.1 Fun-Control FP8 Models for RTX 3060 12GB ==="
echo "This will download ~15GB of models optimized for 12GB VRAM"
echo

# Create directories
mkdir -p models/diffusion_models
mkdir -p models/text_encoders
mkdir -p models/vae
mkdir -p models/clip_vision

echo "📥 Downloading 1.3B Fun-Control Model (fp8 optimized)..."
wget -c --show-progress -O models/diffusion_models/Wan2.1-Fun-1.3B-Control.safetensors \
  "https://huggingface.co/alibaba-pai/Wan2.1-Fun-1.3B-Control/resolve/main/diffusion_pytorch_model.safetensors"

echo "📥 Downloading Text Encoder (fp8 - VRAM efficient)..."
wget -c --show-progress -O models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"

echo "📥 Downloading Alternative Text Encoder (bf16 - more precision)..."
wget -c --show-progress -O models/text_encoders/umt5-xxl-enc-bf16.safetensors \
  "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors"

echo "📥 Downloading VAE..."
wget -c --show-progress -O models/vae/wan_2.1_vae.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors"

echo "📥 Downloading CLIP Vision..."
wget -c --show-progress -O models/clip_vision/clip_vision_h.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors"

echo "📥 Downloading 14B fp8 model (optional, for higher quality when you have more VRAM)..."
wget -c --show-progress -O models/diffusion_models/Wan2.1-Fun-Control-14B_fp8_e4m3fn.safetensors \
  "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2.1-Fun-Control-14B_fp8_e4m3fn.safetensors" || echo "⚠️ 14B model download failed, continuing..."

echo
echo "=== 🎉 Download Complete! ==="
echo "✅ Models downloaded to:"
echo "   📁 Diffusion models: models/diffusion_models/"
echo "   📁 Text encoders: models/text_encoders/"
echo "   📁 VAE: models/vae/"
echo "   📁 CLIP Vision: models/clip_vision/"
echo
echo "🔄 Now restart ComfyUI with VRAM optimization:"
echo "cd /home/ned/ComfyUI-Install/ComfyUI"
echo "source venv/bin/activate"
echo "python main.py --listen 0.0.0.0 --port 8188 --cpu"
echo
echo "💡 Important notes:"
echo "   • Use --cpu flag for CPU offloading (keeps GPU active!)"
echo "   • 1.3B model fits perfectly on RTX 3060 12GB"
echo "   • fp8 precision saves ~50% VRAM vs fp16"
echo "   • 14B model is optional (requires more VRAM)"