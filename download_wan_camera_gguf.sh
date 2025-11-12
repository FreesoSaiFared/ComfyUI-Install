#!/usr/bin/env bash
set -euo pipefail

echo "=== Downloading Wan2.1 Fun-Control Camera GGUF Model ==="
echo "Q8_0 quantized version for memory efficiency on RTX 3060 12GB"
echo

# Create models directory
mkdir -p models/diffusion_models

# Download URL
GGUF_URL="https://huggingface.co/QuantStack/Wan2.1-Fun-V1.1-1.3B-Control-Camera-GGUF/resolve/main/Wan2.1-Fun-V1.1-1.3B-Control-Camera-Q8_0.gguf"
OUTPUT_FILE="models/diffusion_models/Wan2.1-Fun-V1.1-1.3B-Control-Camera-Q8_0.gguf"

echo "📥 Downloading GGUF Camera Control model..."
echo "This provides camera motion control for more dynamic videos"
echo "File size: ~1.7GB (vs 10.5GB for full model)"
echo

# Download with resume capability
if command -v wget >/dev/null 2>&1; then
    echo "Using wget..."
    wget -c --show-progress -O "$OUTPUT_FILE" "$GGUF_URL"
elif command -v curl >/dev/null 2>&1; then
    echo "Using curl..."
    curl -L --retry 5 --retry-delay 3 -C - -o "$OUTPUT_FILE" "$GGUF_URL"
else
    echo "❌ Error: Neither wget nor curl is available"
    exit 1
fi

# Verify download
if [ -f "$OUTPUT_FILE" ]; then
    FILE_SIZE=$(stat -c%s "$OUTPUT_FILE" 2>/dev/null || stat -f%z "$OUTPUT_FILE" 2>/dev/null || echo "unknown")
    echo
    echo "✅ Download complete!"
    echo "📁 File: $OUTPUT_FILE"
    echo "📊 Size: $((FILE_SIZE / 1024 / 1024))MB"
    echo
    echo "🔄 Restart ComfyUI to load the new model:"
    echo "cd /home/ned/ComfyUI-Install/ComfyUI"
    echo "source venv/bin/activate"
    echo "python main.py --listen 0.0.0.0 --port 8188 --force-fp16 --preview-method auto"
    echo
    echo "💡 Usage Tips:"
    echo "• This GGUF model provides camera motion control"
    echo "• Much more VRAM-efficient than the full 10.5GB model"
    echo "• Perfect for RTX 3060 12GB setups"
    echo "• Look for 'WanCameraControl' nodes in ComfyUI"
else
    echo "❌ Download failed - file not found"
    exit 1
fi