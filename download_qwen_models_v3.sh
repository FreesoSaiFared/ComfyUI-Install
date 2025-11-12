#!/bin/bash
#
# Qwen-VL-9B Model Downloader v3 - Fixed HuggingFace CLI usage
# This script uses the correct HuggingFace CLI commands to access the repository
# and download the required models.
#

set -euo pipefail

# --- Configuration ---
COMFYUI_BASE="/home/ned/ComfyUI-Install/ComfyUI"
MODELS_DIR="${COMFYUI_BASE}/models"
REPO_ID="Qwen/Qwen-VL-9B-ComfyUI"

# Model files to download
declare -A MODEL_FILES=(
    ["diffusion"]="qwen_image_9b_wlem3m.safetensors"
    ["encoder"]="qwen_2.5_9b_wlem_scaled.safetensors"
    ["vae"]="qwen_image_vae.safetensors"
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

download_with_hf_cli() {
    local repo_file="$1"
    local target_dir="$2"
    local target_file="$3"

    log "Attempting to download: ${repo_file}"

    # Create target directory
    mkdir -p "${target_dir}"

    # Activate virtual environment
    source "${COMFYUI_BASE}/venv/bin/activate"

    # Use huggingface-cli download
    if huggingface-cli download "${REPO_ID}" "${repo_file}" \
        --token "${HF_TOKEN}" \
        --local-dir "${target_dir}" \
        --local-dir-use-symlinks False \
        --quiet; then

        # Check if file was downloaded successfully
        if [[ -f "${target_dir}/${repo_file}" ]]; then
            # Move file to correct location if needed
            if [[ "${repo_file}" != "${target_file}" ]]; then
                mv "${target_dir}/${repo_file}" "${target_dir}/${target_file}"
            fi
            log "✓ Successfully downloaded ${target_file}"
            return 0
        else
            error "Download command completed but file not found: ${target_dir}/${target_file}"
            return 1
        fi
    else
        error "Failed to download ${repo_file}"
        return 1
    fi
}

download_with_python() {
    local repo_file="$1"
    local target_dir="$2"
    local target_file="$3"

    log "Attempting Python download: ${repo_file}"

    # Create target directory
    mkdir -p "${target_dir}"

    # Activate virtual environment
    source "${COMFYUI_BASE}/venv/bin/activate"

    # Use Python script to download
    python3 << EOF
import os
from huggingface_hub import hf_hub_download, HfApi
import sys

try:
    # Set token
    os.environ['HF_TOKEN'] = '${HF_TOKEN}'

    # Download file
    file_path = hf_hub_download(
        repo_id='${REPO_ID}',
        filename='${repo_file}',
        token='${HF_TOKEN}',
        local_dir='${target_dir}',
        local_dir_use_symlinks=False
    )

    print(f"Successfully downloaded: {file_path}")

    # Check if file exists and has content
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        print(f"File size: {size} bytes")
        if size > 1000000:  # At least 1MB
            print("Download successful!")
            sys.exit(0)
        else:
            print("File too small, download may have failed")
            sys.exit(1)
    else:
        print("File not found after download")
        sys.exit(1)

except Exception as e:
    print(f"Error downloading {repo_file}: {e}")
    sys.exit(1)
EOF

    local result=$?
    if [[ ${result} -eq 0 ]]; then
        log "✓ Successfully downloaded ${target_file} via Python"
        return 0
    else
        error "Failed to download ${repo_file} via Python"
        return 1
    fi
}

# --- Main Execution ---
main() {
    log "Starting Qwen-VL-9B model downloader v3"
    log "Target directory: ${COMFYUI_BASE}"

    # Check requirements
    check_requirements

    log "---------------------------------------------------------"
    log "Attempting to download all Qwen-VL-9B model files..."

    local failed_downloads=()
    local successful_downloads=()

    # Try downloading each model file with different methods
    for model_type in "${!MODEL_FILES[@]}"; do
        local filename="${MODEL_FILES[${model_type}]}"
        local target_dir="${MODELS_DIR}/${model_type}_models"

        # Adjust directory names for text_encoders
        if [[ "${model_type}" == "encoder" ]]; then
            target_dir="${MODELS_DIR}/text_encoders"
        fi

        log "---------------------------------------------------------"
        log "Processing ${model_type} model: ${filename}"

        local download_success=false

        # Method 1: Try direct file path
        log "Method 1: Direct file download"
        if download_with_hf_cli "${filename}" "${target_dir}" "${filename}"; then
            download_success=true
        else
            # Method 2: Try with subdirectory structure
            local subdir="${model_type}_models"
            if [[ "${model_type}" == "encoder" ]]; then
                subdir="text_encoders"
            fi

            log "Method 2: Subdirectory path: ${subdir}/${filename}"
            if download_with_hf_cli "${subdir}/${filename}" "${target_dir}" "${filename}"; then
                download_success=true
            else
                # Method 3: Use Python download method
                log "Method 3: Python download"
                if download_with_python "${filename}" "${target_dir}" "${filename}"; then
                    download_success=true
                else
                    log "Method 4: Python download with subdirectory"
                    if download_with_python "${subdir}/${filename}" "${target_dir}" "${filename}"; then
                        download_success=true
                    fi
                fi
            fi
        fi

        if [[ "${download_success}" == "true" ]]; then
            successful_downloads+=("${model_type}")
        else
            failed_downloads+=("${model_type}")
        fi
    done

    log "---------------------------------------------------------"
    log "Download Summary:"

    if [[ ${#successful_downloads[@]} -gt 0 ]]; then
        log "Successfully downloaded: ${successful_downloads[*]}"
    fi

    if [[ ${#failed_downloads[@]} -gt 0 ]]; then
        error "Failed to download: ${failed_downloads[*]}"
    fi

    # Final verification
    log "---------------------------------------------------------"
    log "Verifying downloaded files..."

    local all_success=true
    local total_size=0

    for model_type in "${!MODEL_FILES[@]}"; do
        local filename="${MODEL_FILES[${model_type}]}"
        local target_dir="${MODELS_DIR}/${model_type}_models"

        if [[ "${model_type}" == "encoder" ]]; then
            target_dir="${MODELS_DIR}/text_encoders"
        fi

        local filepath="${target_dir}/${filename}"

        if [[ -f "${filepath}" ]]; then
            local size
            size=$(stat -c%s "${filepath}")
            total_size=$((total_size + size))

            # Check if file size is reasonable
            local min_size
            case "${model_type}" in
                "diffusion") min_size=10000000000 ;;  # 10GB
                "encoder") min_size=5000000000 ;;     # 5GB
                "vae") min_size=100000000 ;;          # 100MB
            esac

            if [[ ${size} -gt ${min_size} ]]; then
                log "✓ ${filename}: $((size / 1024 / 1024))MB"
            else
                log "✗ ${filename}: Too small (${size} bytes, expected >${min_size})"
                all_success=false
            fi
        else
            log "✗ ${filename}: Missing"
            all_success=false
        fi
    done

    log "Total downloaded: $((total_size / 1024 / 1024))MB"

    # Final status
    if [[ "${all_success}" == "true" ]]; then
        log "🎉 All Qwen-VL-9B models downloaded successfully!"
        log "Please restart ComfyUI to load the new models."
        return 0
    else
        error "Some downloads failed or files are too small."
        error "Please check the errors above and try running the script again."
        return 1
    fi
}

# Run main function
main "$@"