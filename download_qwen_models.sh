#!/bin/bash
#
# Enhanced Qwen-VL-9B Model Downloader for ComfyUI
# Improvements:
# - Better progress reporting with time estimates
# - Enhanced error handling and retry logic
# - Disk space validation before downloads
# - Network connectivity checks
# - Improved logging with timestamps
#

set -euo pipefail  # Exit on any error

# --- Configuration ---
COMFYUI_BASE="/home/ned/ComfyUI-Install/ComfyUI"
MODELS_DIR="${COMFYUI_BASE}/models"
DIFFUSION_DIR="${MODELS_DIR}/diffusion_models"
ENCODER_DIR="${MODELS_DIR}/text_encoders"
VAE_DIR="${MODELS_DIR}/vae"

# Model definitions with expected sizes
declare -A MODELS=(
    ["diffusion"]="qwen_image_9b_wlem3m.safetensors|18.03|https://huggingface.co/Qwen/Qwen-VL-9B-ComfyUI/resolve/main/diffusion_models/qwen_image_9b_wlem3m.safetensors|${DIFFUSION_DIR}"
    ["encoder"]="qwen_2.5_9b_wlem_scaled.safetensors|8.74|https://huggingface.co/Qwen/Qwen-VL-9B-ComfyUI/resolve/main/text_encoders/qwen_2.5_9b_wlem_scaled.safetensors|${ENCODER_DIR}"
    ["vae"]="qwen_image_vae.safetensors|0.24|https://huggingface.co/Qwen/Qwen-VL-9B-ComfyUI/resolve/main/vae/qwen_image_vae.safetensors|${VAE_DIR}"
)

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

    # Check network connectivity
    if ! ping -c 1 huggingface.co >/dev/null 2>&1; then
        error "Cannot reach huggingface.co - check your internet connection"
        exit 1
    fi
    log "✓ Network connectivity verified"

    # Check disk space (need at least 30GB free)
    local available_space
    available_space=$(df "${MODELS_DIR}" | awk 'NR==2 {print $4}')
    local required_space=$((30 * 1024 * 1024))  # 30GB in KB
    if [[ ${available_space} -lt ${required_space} ]]; then
        error "Insufficient disk space. Need ~30GB, available: $((available_space / 1024 / 1024))GB"
        exit 1
    fi
    log "✓ Sufficient disk space available"

    # Check ComfyUI directory
    if [[ ! -d "${COMFYUI_BASE}" ]]; then
        error "ComfyUI directory not found: ${COMFYUI_BASE}"
        exit 1
    fi
    log "✓ ComfyUI directory verified"
}

clean_failed_download() {
    local filepath="$1"
    if [[ -f "${filepath}" ]]; then
        local filesize
        filesize=$(stat -c%s "${filepath}")
        if [[ ${filesize} -lt 1048576 ]]; then  # Less than 1MB
            log "Removing failed download: ${filepath} (${filesize} bytes)"
            rm -f "${filepath}"
        fi
    fi
}

download_model() {
    local model_type="$1"
    local model_info="${MODELS[${model_type}]}"

    IFS='|' read -r filename expected_size url target_dir <<< "${model_info}"

    local filepath="${target_dir}/${filename}"
    local expected_bytes
    expected_bytes=$(echo "${expected_size}" | awk '{printf "%.0f", $1 * 1024 * 1024 * 1024}')

    log "Starting download: ${filename} (${expected_size}GB)"

    # Create target directory
    mkdir -p "${target_dir}"

    # Clean any failed downloads
    clean_failed_download "${filepath}"

    # Skip if already downloaded and correct size
    if [[ -f "${filepath}" ]]; then
        local actual_size
        actual_size=$(stat -c%s "${filepath}")
        local size_diff
        size_diff=$((actual_size - expected_bytes))

        if [[ ${size_diff#-} -lt 10485760 ]]; then  # Within 10MB
            log "✓ ${filename} already exists with correct size. Skipping."
            return 0
        else
            log "File exists but size mismatch. Re-downloading..."
            rm -f "${filepath}"
        fi
    fi

    # Prepare authentication
    local auth_args=("--header=Authorization: Bearer ${HF_TOKEN}")

    # Download with retry logic
    local max_attempts=3
    local attempt=1

    while [[ ${attempt} -le ${max_attempts} ]]; do
        log "Download attempt ${attempt}/${max_attempts} for ${filename}"

        if wget --progress=bar:force \
                --timeout=300 \
                --tries=2 \
                --retry-connrefused \
                --continue \
                "${auth_args[@]}" \
                -O "${filepath}" \
                "${url}" 2>&1 | tee /tmp/wget_progress.log; then

            # Verify download size
            if [[ -f "${filepath}" ]]; then
                local downloaded_size
                downloaded_size=$(stat -c%s "${filepath}")
                if [[ ${downloaded_size} -gt ${expected_bytes} ]]; then
                    log "✓ Successfully downloaded ${filename} ($((downloaded_size / 1024 / 1024))MB)"
                    return 0
                else
                    error "Downloaded file too small: ${downloaded_size} bytes (expected: ${expected_bytes})"
                    rm -f "${filepath}"
                fi
            fi
        else
            error "Download failed for attempt ${attempt}"
        fi

        ((attempt++))
        if [[ ${attempt} -le ${max_attempts} ]]; then
            log "Waiting 10 seconds before retry..."
            sleep 10
        fi
    done

    error "Failed to download ${filename} after ${max_attempts} attempts"
    return 1
}

# --- Main Execution ---
main() {
    log "Starting enhanced Qwen-VL-9B model downloader"
    log "Target directory: ${COMFYUI_BASE}"

    # Check all requirements
    check_requirements

    log "---------------------------------------------------------"

    # Download each model
    local failed_models=()

    for model_type in "${!MODELS[@]}"; do
        if ! download_model "${model_type}"; then
            failed_models+=("${model_type}")
        fi
        log "---------------------------------------------------------"
    done

    # Final status
    if [[ ${#failed_models[@]} -eq 0 ]]; then
        log "🎉 All models downloaded successfully!"
        log "Total downloaded models: ${#MODELS[@]}"

        # Verify final state
        log "Final verification:"
        for model_type in "${!MODELS[@]}"; do
            local model_info="${MODELS[${model_type}]}"
            IFS='|' read -r filename _ _ target_dir <<< "${model_info}"
            local filepath="${target_dir}/${filename}"
            if [[ -f "${filepath}" ]]; then
                local size
                size=$(stat -c%s "${filepath}")
                log "  ✓ ${filename}: $((size / 1024 / 1024))MB"
            else
                log "  ✗ ${filename}: MISSING"
            fi
        done

        log "Please restart ComfyUI to load the new models."
        return 0
    else
        error "Failed to download models: ${failed_models[*]}"
        error "Please check the error messages above and try again."
        return 1
    fi
}

# Run main function
main "$@"