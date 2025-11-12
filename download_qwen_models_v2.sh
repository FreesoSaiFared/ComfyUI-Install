#!/bin/bash
#
# Qwen-VL-9B Model Downloader v2 - Uses HuggingFace CLI for better access
# This script uses the HuggingFace CLI to properly access the repository
# and download the required models with correct paths.
#

set -euo pipefail

# --- Configuration ---
COMFYUI_BASE="/home/ned/ComfyUI-Install/ComfyUI"
MODELS_DIR="${COMFYUI_BASE}/models"
REPO_ID="Qwen/Qwen-VL-9B-ComfyUI"

# --- Utility Functions ---
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

check_requirements() {
    log "Checking system requirements..."

    # Check HF Token
    if [[ -z "${HF_TOKEN:-}" ]]; then
        error "HF_TOKEN environment variable is not set"
        error "Get a token from: https://huggingface.co/settings/tokens"
        error "Then run: export HF_TOKEN=\"hf_YOUR_TOKEN\""
        exit 1
    fi
    log "✓ HF Token is configured"

    # Check if huggingface-hub is installed
    if ! python3 -c "import huggingface_hub" 2>/dev/null; then
        log "Installing huggingface-hub..."
        source "${COMFYUI_BASE}/venv/bin/activate"
        pip install huggingface_hub
    fi
    log "✓ HuggingFace Hub available"

    # Check ComfyUI directory
    if [[ ! -d "${COMFYUI_BASE}" ]]; then
        error "ComfyUI directory not found: ${COMFYUI_BASE}"
        exit 1
    fi
    log "✓ ComfyUI directory verified"
}

download_model_file() {
    local file_path="$1"
    local target_dir="$2"
    local target_file="$3"

    log "Downloading: ${file_path} -> ${target_dir}/${target_file}"

    # Create target directory
    mkdir -p "${target_dir}"

    # Use huggingface-cli download with authentication
    source "${COMFYUI_BASE}/venv/bin/activate"

    if huggingface-cli download "${REPO_ID}" "${file_path}" \
        --token "${HF_TOKEN}" \
        --local-dir "${target_dir}" \
        --local-dir-use-symlinks False; then

        log "✓ Successfully downloaded ${target_file}"
        return 0
    else
        error "Failed to download ${target_file}"
        return 1
    fi
}

# --- Main Execution ---
main() {
    log "Starting Qwen-VL-9B model downloader v2 using HuggingFace CLI"
    log "Target directory: ${COMFYUI_BASE}"

    # Check requirements
    check_requirements

    log "---------------------------------------------------------"

    # Activate virtual environment
    source "${COMFYUI_BASE}/venv/bin/activate"

    # List files in the repository to get correct paths
    log "Discovering available files in repository..."
    if ! huggingface-cli files "${REPO_ID}" --token "${HF_TOKEN}"; then
        error "Cannot access repository. Please check your HF token and repository access."
        exit 1
    fi

    log "---------------------------------------------------------"
    log "Starting model downloads..."

    # Try different possible file paths based on typical ComfyUI structure
    local failed_downloads=()

    # Diffusion model attempts
    log "Attempting to download diffusion models..."

    # Method 1: Try the expected structure
    if download_model_file "diffusion_models/qwen_image_9b_wlem3m.safetensors" "${MODELS_DIR}/diffusion_models" "qwen_image_9b_wlem3m.safetensors"; then
        log "✓ Diffusion model downloaded successfully"
    else
        # Method 2: Try direct file in root
        log "Trying alternative path for diffusion model..."
        if download_model_file "qwen_image_9b_wlem3m.safetensors" "${MODELS_DIR}/diffusion_models" "qwen_image_9b_wlem3m.safetensors"; then
            log "✓ Diffusion model downloaded successfully (alternative path)"
        else
            failed_downloads+=("diffusion_model")
        fi
    fi

    # Text encoder attempts
    log "Attempting to download text encoders..."

    if download_model_file "text_encoders/qwen_2.5_9b_wlem_scaled.safetensors" "${MODELS_DIR}/text_encoders" "qwen_2.5_9b_wlem_scaled.safetensors"; then
        log "✓ Text encoder downloaded successfully"
    else
        log "Trying alternative path for text encoder..."
        if download_model_file "qwen_2.5_9b_wlem_scaled.safetensors" "${MODELS_DIR}/text_encoders" "qwen_2.5_9b_wlem_scaled.safetensors"; then
            log "✓ Text encoder downloaded successfully (alternative path)"
        else
            failed_downloads+=("text_encoder")
        fi
    fi

    # VAE attempts
    log "Attempting to download VAE..."

    if download_model_file "vae/qwen_image_vae.safetensors" "${MODELS_DIR}/vae" "qwen_image_vae.safetensors"; then
        log "✓ VAE downloaded successfully"
    else
        log "Trying alternative path for VAE..."
        if download_model_file "qwen_image_vae.safetensors" "${MODELS_DIR}/vae" "qwen_image_vae.safetensors"; then
            log "✓ VAE downloaded successfully (alternative path)"
        else
            failed_downloads+=("vae")
        fi
    fi

    log "---------------------------------------------------------"

    # Final verification
    log "Verifying downloads..."
    local all_success=true

    # Check diffusion model
    if [[ -f "${MODELS_DIR}/diffusion_models/qwen_image_9b_wlem3m.safetensors" ]]; then
        local size
        size=$(stat -c%s "${MODELS_DIR}/diffusion_models/qwen_image_9b_wlem3m.safetensors")
        if [[ ${size} -gt 1000000000 ]]; then  # > 1GB
            log "✓ Diffusion model: $((size / 1024 / 1024))MB"
        else
            log "✗ Diffusion model: Too small (${size} bytes)"
            all_success=false
        fi
    else
        log "✗ Diffusion model: Missing"
        all_success=false
    fi

    # Check text encoder
    if [[ -f "${MODELS_DIR}/text_encoders/qwen_2.5_9b_wlem_scaled.safetensors" ]]; then
        local size
        size=$(stat -c%s "${MODELS_DIR}/text_encoders/qwen_2.5_9b_wlem_scaled.safetensors")
        if [[ ${size} -gt 1000000000 ]]; then  # > 1GB
            log "✓ Text encoder: $((size / 1024 / 1024))MB"
        else
            log "✗ Text encoder: Too small (${size} bytes)"
            all_success=false
        fi
    else
        log "✗ Text encoder: Missing"
        all_success=false
    fi

    # Check VAE
    if [[ -f "${MODELS_DIR}/vae/qwen_image_vae.safetensors" ]]; then
        local size
        size=$(stat -c%s "${MODELS_DIR}/vae/qwen_image_vae.safetensors")
        if [[ ${size} -gt 100000000 ]]; then  # > 100MB
            log "✓ VAE: $((size / 1024 / 1024))MB"
        else
            log "✗ VAE: Too small (${size} bytes)"
            all_success=false
        fi
    else
        log "✗ VAE: Missing"
        all_success=false
    fi

    # Final status
    if [[ "${all_success}" == "true" ]]; then
        log "🎉 All Qwen-VL-9B models downloaded successfully!"
        log "Please restart ComfyUI to load the new models."
        return 0
    else
        error "Some downloads failed. Please check the errors above."
        if [[ ${#failed_downloads[@]} -gt 0 ]]; then
            error "Failed downloads: ${failed_downloads[*]}"
        fi
        return 1
    fi
}

# Run main function
main "$@"