#!/bin/bash
#
# Comprehensive Qwen-VL Model Downloader for ComfyUI
# This script tries multiple repositories and methods to download Qwen-VL models
# that are compatible with ComfyUI workflows.
#

set -euo pipefail

# --- Configuration ---
COMFYUI_BASE="/home/ned/ComfyUI-Install/ComfyUI"
MODELS_DIR="${COMFYUI_BASE}/models"

# Target files (based on original script requirements)
TARGET_FILES=(
    "qwen_image_9b_wlem3m.safetensors"
    "qwen_2.5_9b_wlem_scaled.safetensors"
    "qwen_image_vae.safetensors"
)

# Repositories to try
REPOSITORIES=(
    "Qwen/Qwen-VL-9B-ComfyUI"
    "Qwen/Qwen-VL"
    "Qwen/Qwen-VL-Chat"
    "Qwen/Qwen2-VL-7B-Instruct"
    "openbmb/MiniCPM-V-2_6"
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
        exit 1
    fi
    log "✓ HF Token is configured"

    # Check ComfyUI directory
    if [[ ! -d "${COMFYUI_BASE}" ]]; then
        error "ComfyUI directory not found: ${COMFYUI_BASE}"
        exit 1
    fi
    log "✓ ComfyUI directory verified"
}

download_file() {
    local repo_id="$1"
    local filename="$2"
    local target_dir="$3"

    log "Attempting to download ${filename} from ${repo_id}"

    # Create target directory
    mkdir -p "${target_dir}"

    # Activate virtual environment
    source "${COMFYUI_BASE}/venv/bin/activate"

    # Use Python to download with progress tracking
    python3 << EOF
import os
import sys
from huggingface_hub import hf_hub_download, HfApi, RepositoryNotFoundError
import requests
from tqdm import tqdm

repo_id = "${repo_id}"
filename = "${filename}"
target_dir = "${target_dir}"
hf_token = "${HF_TOKEN}"

try:
    # Method 1: Try direct download
    log_msg = f"Trying direct download: {repo_id}/{filename}"
    print(log_msg)

    file_path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        token=hf_token,
        local_dir=target_dir,
        local_dir_use_symlinks=False,
        resume_download=True
    )

    # Verify file size
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        print(f"Downloaded: {file_path} ({size:,} bytes)")

        # Check if file size is reasonable
        if size > 1000000:  # At least 1MB
            print("✓ Download successful!")
            sys.exit(0)
        else:
            print("✗ File too small, may be corrupted")
            os.remove(file_path)
            sys.exit(1)
    else:
        print("✗ File not found after download")
        sys.exit(1)

except RepositoryNotFoundError:
    print(f"✗ Repository not found: {repo_id}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error downloading {filename}: {e}")
    sys.exit(1)
EOF

    local result=$?
    if [[ ${result} -eq 0 ]]; then
        return 0
    else
        return 1
    fi
}

download_with_wget() {
    local url="$1"
    local target_path="$2"
    local auth_header="$3"

    log "Trying wget download: ${url}"

    # Clean any existing 0-byte files
    if [[ -f "${target_path}" ]]; then
        local size
        size=$(stat -c%s "${target_path}")
        if [[ ${size} -lt 1024 ]]; then
            rm -f "${target_path}"
        fi
    fi

    # Download with wget
    if wget --continue \
            --timeout=300 \
            --tries=3 \
            --retry-connrefused \
            --progress=bar:force \
            "${auth_header}" \
            -O "${target_path}" \
            "${url}"; then

        # Verify download
        if [[ -f "${target_path}" ]]; then
            local size
            size=$(stat -c%s "${target_path}")
            if [[ ${size} -gt 1000000 ]]; then  # At least 1MB
                log "✓ Successfully downloaded $(basename "${target_path}") ($((size / 1024 / 1024))MB)"
                return 0
            else
                error "Downloaded file too small: ${size} bytes"
                rm -f "${target_path}"
            fi
        fi
    fi

    return 1
}

# --- Main Execution ---
main() {
    log "Starting comprehensive Qwen-VL model downloader"
    log "Target directory: ${COMFYUI_BASE}"

    # Check requirements
    check_requirements

    log "---------------------------------------------------------"
    log "Attempting to download Qwen-VL models from multiple sources..."

    local success_count=0
    local target_count=${#TARGET_FILES[@]}

    # For each target file, try different repositories and methods
    for target_file in "${TARGET_FILES[@]}"; do
        log "========================================================="
        log "Looking for: ${target_file}"

        local downloaded=false
        local target_dir=""

        # Determine target directory based on file type
        if [[ "${target_file}" == *"image_9b"* ]]; then
            target_dir="${MODELS_DIR}/diffusion_models"
        elif [[ "${target_file}" == *"2.5_9b"* ]]; then
            target_dir="${MODELS_DIR}/text_encoders"
        elif [[ "${target_file}" == *"vae"* ]]; then
            target_dir="${MODELS_DIR}/vae"
        else
            target_dir="${MODELS_DIR}/other"
        fi

        # Create target directory
        mkdir -p "${target_dir}"
        local target_path="${target_dir}/${target_file}"

        # Method 1: Try different repositories with HuggingFace Hub
        for repo in "${REPOSITORIES[@]}"; do
            if download_file "${repo}" "${target_file}" "${target_dir}"; then
                downloaded=true
                success_count=$((success_count + 1))
                break
            fi
        done

        # Method 2: Try direct URLs (from original script)
        if [[ "${downloaded}" == "false" ]]; then
            log "Trying direct URLs from original script..."

            local auth_args=("--header=Authorization: Bearer ${HF_TOKEN}")

            case "${target_file}" in
                "qwen_image_9b_wlem3m.safetensors")
                    local url="https://huggingface.co/Qwen/Qwen-VL-9B-ComfyUI/resolve/main/diffusion_models/qwen_image_9b_wlem3m.safetensors"
                    ;;
                "qwen_2.5_9b_wlem_scaled.safetensors")
                    local url="https://huggingface.co/Qwen/Qwen-VL-9B-ComfyUI/resolve/main/text_encoders/qwen_2.5_9b_wlem_scaled.safetensors"
                    ;;
                "qwen_image_vae.safetensors")
                    local url="https://huggingface.co/Qwen/Qwen-VL-9B-ComfyUI/resolve/main/vae/qwen_image_vae.safetensors"
                    ;;
                *)
                    continue
                    ;;
            esac

            if download_with_wget "${url}" "${target_path}" "${auth_args[@]}"; then
                downloaded=true
                success_count=$((success_count + 1))
            fi
        fi

        # Method 3: Try alternative direct URLs
        if [[ "${downloaded}" == "false" ]]; then
            log "Trying alternative URLs..."

            # Try without subdirectories
            local base_url="https://huggingface.co/Qwen/Qwen-VL-9B-ComfyUI/resolve/main/${target_file}"
            local auth_args=("--header=Authorization: Bearer ${HF_TOKEN}")

            if download_with_wget "${base_url}" "${target_path}" "${auth_args[@]}"; then
                downloaded=true
                success_count=$((success_count + 1))
            fi
        fi

        if [[ "${downloaded}" == "true" ]]; then
            log "✓ Successfully obtained: ${target_file}"
        else
            error "✗ Failed to download: ${target_file}"
        fi
    done

    # Final verification
    log "========================================================="
    log "Final verification and summary:"
    log "Successfully downloaded: ${success_count}/${target_count} files"

    local total_size=0
    local all_valid=true

    for target_file in "${TARGET_FILES[@]}"; do
        # Determine target directory
        if [[ "${target_file}" == *"image_9b"* ]]; then
            target_dir="${MODELS_DIR}/diffusion_models"
        elif [[ "${target_file}" == *"2.5_9b"* ]]; then
            target_dir="${MODELS_DIR}/text_encoders"
        elif [[ "${target_file}" == *"vae"* ]]; then
            target_dir="${MODELS_DIR}/vae"
        else
            target_dir="${MODELS_DIR}/other"
        fi

        local filepath="${target_dir}/${target_file}"

        if [[ -f "${filepath}" ]]; then
            local size
            size=$(stat -c%s "${filepath}")
            total_size=$((total_size + size))

            # Expected minimum sizes
            local min_size
            case "${target_file}" in
                "qwen_image_9b_wlem3m.safetensors") min_size=10000000000 ;;  # 10GB
                "qwen_2.5_9b_wlem_scaled.safetensors") min_size=5000000000 ;;  # 5GB
                "qwen_image_vae.safetensors") min_size=100000000 ;;  # 100MB
                *) min_size=1000000 ;;  # 1MB default
            esac

            if [[ ${size} -gt ${min_size} ]]; then
                log "  ✓ ${target_file}: $((size / 1024 / 1024))MB"
            else
                log "  ✗ ${target_file}: Too small (${size} bytes, expected >${min_size})"
                all_valid=false
            fi
        else
            log "  ✗ ${target_file}: Missing"
            all_valid=false
        fi
    done

    log "Total downloaded: $((total_size / 1024 / 1024))MB"

    # Final status
    if [[ "${all_valid}" == "true" ]]; then
        log "🎉 All Qwen-VL models downloaded successfully!"
        log "Please restart ComfyUI to load the new models."

        # Check if ComfyUI is running and offer to restart
        if pgrep -f "main.py" > /dev/null; then
            log "ComfyUI appears to be running. Consider restarting it to load the new models."
        fi

        return 0
    else
        error "Some downloads failed or files are invalid."
        error "The specific ComfyUI-compatible Qwen-VL models may not be available"
        error "or may require different repository names/paths."
        error ""
        error "Suggestions:"
        error "1. Check if you need access to a private/gated repository"
        error "2. Verify the exact file names and repository structure"
        error "3. Consider alternative Qwen-VL implementations for ComfyUI"
        return 1
    fi
}

# Run main function
main "$@"