#!/usr/bin/env bash
set -euo pipefail

# ==== Config ====
: "${COMFY:=${HOME}/ComfyUI-Install/ComfyUI}"          # Set your ComfyUI path if different
WAN_SIZE="${WAN_SIZE:-1.3B}"           # choose: 1.3B or 14B (export WAN_SIZE=14B to get 14B)
ENC_PREF="${ENC_PREF:-fp8}"            # choose: fp8 or bf16 (text encoder); both will be installed
PARALLEL="${PARALLEL:-4}"              # parallel connections for wget/curl if used

echo "== Wan2.1 Fun-Control setup (v2) =="
echo "COMFY:      $COMFY"
echo "WAN_SIZE:   $WAN_SIZE"
echo "ENC_PREF:   $ENC_PREF"
echo

# ==== Ensure dirs ====
mkdir -p "${COMFY}/custom_nodes"
mkdir -p "${COMFY}/models/diffusion_models"
mkdir -p "${COMFY}/models/text_encoders"
mkdir -p "${COMFY}/models/vae"
mkdir -p "${COMFY}/models/clip_vision"

cd "${COMFY}/custom_nodes"

# ==== Install / Update custom nodes ====
clone_or_update () {
  local repo_url="$1"
  local dir_name="$(basename "$repo_url" .git)"
  if [ -d "$dir_name/.git" ]; then
    echo "-- Updating $dir_name"
    git -C "$dir_name" pull --rebase --autostash || echo "   Update failed, continuing..."
  else
    echo "-- Cloning $dir_name"
    git clone --depth=1 "$repo_url" || echo "   Clone failed, continuing..."
  fi
}

# Install required nodes
echo "=== Installing/Updating Custom Nodes ==="
clone_or_update https://github.com/kijai/ComfyUI-WanVideoWrapper.git
clone_or_update https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
clone_or_update https://github.com/kijai/ComfyUI-KJNodes.git
clone_or_update https://github.com/Fannovel16/comfyui_controlnet_aux.git

echo
echo "=== Installing Dependencies ==="
# Install dependencies for each node if requirements.txt exists
for node_dir in ComfyUI-WanVideoWrapper ComfyUI-VideoHelperSuite ComfyUI-KJNodes comfyui_controlnet_aux; do
    if [ -d "$node_dir" ] && [ -f "$node_dir/requirements.txt" ]; then
        echo "-- Installing dependencies for $node_dir"
        cd "$node_dir"
        source "${COMFY}/venv/bin/activate"
        pip install -r requirements.txt || echo "   Pip install failed for $node_dir, continuing..."
        cd ..
    fi
done

cd "${COMFY}/custom_nodes"

# ==== Model URLs ====
# Diffusion (pick 1.3B or 14B from Alibaba PAI)
if [ "$WAN_SIZE" = "14B" ]; then
  WAN_URL="https://huggingface.co/alibaba-pai/Wan2.1-Fun-14B-Control/blob/main/diffusion_pytorch_model.safetensors?download=true"
  WAN_OUT="Wan2.1-Fun-14B-Control.safetensors"
else
  WAN_URL="https://huggingface.co/alibaba-pai/Wan2.1-Fun-1.3B-Control/blob/main/diffusion_pytorch_model.safetensors?download=true"
  WAN_OUT="Wan2.1-Fun-1.3B-Control.safetensors"
fi

# Optional: Kijai fp8 packaged 14B fun-control (some users prefer this variant)
KJ_WAN14B_FP8_URL="https://huggingface.co/Kijai/WanVideo_comfy/blob/main/Wan2.1-Fun-Control-14B_fp8_e4m3fn.safetensors?download=true"
KJ_WAN14B_FP8_OUT="Wan2.1-Fun-Control-14B_fp8_e4m3fn.safetensors"

# Text encoders (both variants so you can switch in-node)
# Native repackaged:
UFM_FP16_URL="https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp16.safetensors?download=true"
UFM_FP8_URL="https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors?download=true"
# Kijai variants:
KJ_BF16_URL="https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors?download=true"
KJ_FP8_URL="https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-fp8_e4m3fn.safetensors?download=true"

# VAE (native + kijai)
VAE_NATIVE_URL="https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors?download=true"
VAE_NATIVE_OUT="wan_2.1_vae.safetensors"
KJ_VAE_FP32_URL="https://huggingface.co/Kijai/WanVideo_comfy/blob/main/Wan2_1_VAE_fp32.safetensors?download=true"
KJ_VAE_BF16_URL="https://huggingface.co/Kijai/WanVideo_comfy/blob/main/Wan2_1_VAE_bf16.safetensors?download=true"

# CLIP Vision
CLIP_V_URL="https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors?download=true"
CLIP_V_OUT="clip_vision_h.safetensors"

dl() {  # curl downloader with resume & follow
  local url="$1"; local out="$2"; local dest="$3"
  if [ -f "${dest}/${out}" ]; then
    local size
    size=$(stat -c%s "${dest}/${out}" 2>/dev/null || echo "0")
    if [ "$size" -gt 1000000 ]; then  # > 1MB
      echo "   exists: ${dest}/${out} ($((size / 1024 / 1024))MB)"
    else
      echo "   exists but small: ${dest}/${out} (${size} bytes) - re-downloading"
      echo "   downloading: ${out}"
      curl -L --retry 5 --retry-delay 3 -C - -o "${dest}/${out}.part" "$url"
      mv "${dest}/${out}.part" "${dest}/${out}"
    fi
  else
    echo "   downloading: ${out}"
    curl -L --retry 5 --retry-delay 3 -o "${dest}/${out}.part" "$url"
    mv "${dest}/${out}.part" "${dest}/${out}"
  fi
}

echo
echo "=== Downloading Models ==="

echo "-- Downloading diffusion: ${WAN_OUT}"
dl "$WAN_URL" "$WAN_OUT" "${COMFY}/models/diffusion_models"

echo "-- (Optional) Kijai packed 14B fp8 (kept side-by-side)"
dl "$KJ_WAN14B_FP8_URL" "$KJ_WAN14B_FP8_OUT" "${COMFY}/models/diffusion_models" || echo "   Failed to download optional 14B fp8 model"

echo "-- Downloading text encoders"
dl "$UFM_FP16_URL" "umt5_xxl_fp16.safetensors" "${COMFY}/models/text_encoders"
dl "$UFM_FP8_URL"  "umt5_xxl_fp8_e4m3fn_scaled.safetensors" "${COMFY}/models/text_encoders"
dl "$KJ_BF16_URL"  "umt5-xxl-enc-bf16.safetensors" "${COMFY}/models/text_encoders"
dl "$KJ_FP8_URL"   "umt5-xxl-enc-fp8_e4m3fn.safetensors" "${COMFY}/models/text_encoders"

echo "-- Downloading VAE"
dl "$VAE_NATIVE_URL" "$VAE_NATIVE_OUT" "${COMFY}/models/vae"
dl "$KJ_VAE_FP32_URL" "Wan2_1_VAE_fp32.safetensors" "${COMFY}/models/vae"
dl "$KJ_VAE_BF16_URL" "Wan2_1_VAE_bf16.safetensors" "${COMFY}/models/vae"

echo "-- Downloading CLIP Vision"
dl "$CLIP_V_URL" "$CLIP_V_OUT" "${COMFY}/models/clip_vision"

echo
echo "== Installation Complete =="
echo "Models installed in: ${COMFY}/models"
echo
echo "== Model Tree =="
( cd "${COMFY}/models" && find . -maxdepth 2 -type f -name "*.safetensors" | sort )

echo
echo "== Usage Tips =="
echo "Restart ComfyUI. In native flow, use:"
echo "  - Diffusion: ${WAN_OUT}"
echo "  - Text: choose one of: umt5_xxl_fp16 / umt5_xxl_fp8_e4m3fn_scaled / umt5-xxl-enc-bf16 / umt5-xxl-enc-fp8_e4m3fn"
echo "  - VAE: wan_2.1_vae.safetensors (native) OR Wan2_1_VAE_bf16/fp32 (Kijai)"
echo "  - CLIP Vision: clip_vision_h.safetensors"
echo
echo "For Kijai wrapper workflows:"
echo "  - Use WanVideo Model Loader with ${WAN_OUT}"
echo "  - Load T5 Text Encoder with your preferred umt5 variant"
echo "  - Use WanVideo VAE Loader with Wan2_1_VAE_bf16.safetensors"