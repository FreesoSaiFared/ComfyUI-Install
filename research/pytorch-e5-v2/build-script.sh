#!/bin/bash

# PyTorch Compilation Script for Intel Xeon E5 v2 + RTX 3060 12GB
# This script automates the compilation process with proper flags for legacy CPUs

set -e  # Exit on any error

# Configuration variables
PYTORCH_VERSION=${1:-"v2.4.0"}
CUDA_VERSION=${2:-"12.4"}
BUILD_DIR=${3:-"/tmp/pytorch-build"}
MAX_JOBS=${4:-"8"}

echo "=== PyTorch Compilation Script for Intel Xeon E5 v2 ==="
echo "PyTorch Version: $PYTORCH_VERSION"
echo "CUDA Version: $CUDA_VERSION"
echo "Build Directory: $BUILD_DIR"
echo "Max Jobs: $MAX_JOBS"
echo ""

# Function to check system requirements
check_requirements() {
    echo "=== Checking System Requirements ==="

    # Check if CUDA is installed
    if ! command -v nvcc &> /dev/null; then
        echo "❌ CUDA toolkit not found. Please install CUDA $CUDA_VERSION first."
        exit 1
    fi
    echo "✅ CUDA found: $(nvcc --version | grep 'release' | awk '{print $6}' | cut -c2-)"

    # Check GPU
    if ! command -v nvidia-smi &> /dev/null; then
        echo "❌ nvidia-smi not found. Please install NVIDIA drivers."
        exit 1
    fi
    echo "✅ GPU found: $(nvidia-smi --query-gpu=name --format=csv,noheader,nounits | head -1)"

    # Check compiler
    if ! command -v gcc &> /dev/null; then
        echo "❌ GCC not found. Please install build-essential."
        exit 1
    fi
    echo "✅ GCC found: $(gcc --version | head -1)"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 not found."
        exit 1
    fi
    echo "✅ Python found: $(python3 --version)"

    # Check CPU instruction set support
    echo "Checking CPU instruction set support..."
    if grep -q "avx" /proc/cpuinfo; then
        echo "✅ AVX supported"
    else
        echo "❌ AVX not supported. This CPU may not be compatible."
        exit 1
    fi

    if grep -q "avx2" /proc/cpuinfo; then
        echo "⚠️  AVX2 detected - this script is for CPUs without AVX2"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "✅ AVX2 not detected (expected for E5 v2)"
    fi

    echo ""
}

# Function to install dependencies
install_dependencies() {
    echo "=== Installing Dependencies ==="

    # Update package lists
    sudo apt update

    # Install system dependencies
    sudo apt install -y build-essential cmake git python3-dev python3-pip \
        wget curl libopenblas-dev liblapack-dev

    # Install Python dependencies
    python3 -m pip install --upgrade pip
    python3 -m pip install numpy pyyaml typing_extensions setuptools

    echo "✅ Dependencies installed"
    echo ""
}

# Function to download and compile PyTorch
compile_pytorch() {
    echo "=== Downloading and Compiling PyTorch ==="

    # Create build directory
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"

    # Clone PyTorch if not already present
    if [ ! -d "pytorch" ]; then
        echo "Cloning PyTorch repository..."
        git clone https://github.com/pytorch/pytorch.git
    fi

    cd pytorch

    # Checkout desired version
    echo "Checking out PyTorch $PYTORCH_VERSION..."
    git checkout "$PYTORCH_VERSION"
    git submodule sync
    git submodule update --init --recursive

    # Create build directory
    rm -rf build
    mkdir build && cd build

    # Configure CMake
    echo "Configuring CMake..."
    cmake \
        -DCMAKE_BUILD_TYPE=Release \
        -DUSE_CUDA=ON \
        -DCUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda \
        -DCMAKE_CXX_FLAGS="-O3 -march=x86-64 -mavx -mfma" \
        -DCMAKE_C_FLAGS="-O3 -march=x86-64 -mavx -mfma" \
        -DCPU_CAPABILITY_NAMES="DEFAULT;AVX" \
        -DCPU_CAPABILITY_FLAGS=";-mavx" \
        -DUSE_AVX2=OFF \
        -DUSE_AVX512=OFF \
        -DTORCH_CUDA_ARCH_LIST="8.6" \
        -DBUILD_TEST=OFF \
        -DCMAKE_INSTALL_PREFIX="$BUILD_DIR/pytorch-install" \
        ..

    # Build PyTorch
    echo "Building PyTorch (this may take 1-3 hours)..."
    export MAX_JOBS="$MAX_JOBS"
    python3 setup.py develop

    echo "✅ PyTorch compilation completed"
    echo ""
}

# Function to test installation
test_installation() {
    echo "=== Testing PyTorch Installation ==="

    cd "$BUILD_DIR/pytorch"

    # Create test script
    cat > test_pytorch.py << 'EOF'
import torch
import platform
import sys

def test_pytorch():
    print("=== PyTorch Installation Test ===")
    print(f"Python: {sys.version}")
    print(f"System: {platform.system()} {platform.release()}")
    print(f"Processor: {platform.processor()}")
    print(f"PyTorch Version: {torch.__version__}")
    print(f"PyTorch Build: {torch.__config__.show()}")

    # Test CUDA
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")

    if cuda_available:
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"GPU Count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")

        # Test GPU operations
        print("Testing GPU operations...")
        x = torch.randn(1000, 1000, device='cuda')
        y = torch.mm(x, x.t())
        result = y.sum()
        print(f"GPU computation result: {result.item():.4f}")
        print("✅ GPU operations working")
    else:
        print("⚠️  CUDA not available - GPU operations will not work")

    # Test CPU operations
    print("Testing CPU operations...")
    x = torch.randn(1000, 1000)
    y = torch.mm(x, x.t())
    result = y.sum()
    print(f"CPU computation result: {result.item():.4f}")
    print("✅ CPU operations working")

    # Test model creation and training
    print("Testing model operations...")
    device = torch.device('cuda' if cuda_available else 'cpu')
    model = torch.nn.Sequential(
        torch.nn.Linear(1000, 512),
        torch.nn.ReLU(),
        torch.nn.Linear(512, 10)
    ).to(device)

    x = torch.randn(32, 1000).to(device)
    output = model(x)
    print(f"Model output shape: {output.shape}")
    print("✅ Model operations working")

    print("=== All tests completed successfully! ===")

if __name__ == "__main__":
    test_pytorch()
EOF

    # Run test
    python3 test_pytorch.py

    echo ""
}

# Function to create environment setup script
create_env_setup() {
    echo "=== Creating Environment Setup Script ==="

    cat > "$BUILD_DIR/setup-pytorch-env.sh" << EOF
#!/bin/bash

# PyTorch Environment Setup for Intel Xeon E5 v2 + RTX 3060
# Source this script to set up your environment

export PYTORCH_ROOT="$BUILD_DIR/pytorch"
export PYTHONPATH="\$PYTHONPATH:\$PYTORCH_ROOT"
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:\$LD_LIBRARY_PATH"

# Force appropriate CPU capability for E5 v2
export ATEN_CPU_CAPABILITY=default

# Display system info
echo "PyTorch environment configured for Intel Xeon E5 v2"
echo "PyTorch Root: \$PYTORCH_ROOT"
echo "CPU Capability: \$ATEN_CPU_CAPABILITY"
echo ""
echo "To test PyTorch:"
echo "python3 -c \"import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}')\""
EOF

    chmod +x "$BUILD_DIR/setup-pytorch-env.sh"

    echo "✅ Environment setup script created: $BUILD_DIR/setup-pytorch-env.sh"
    echo ""
}

# Main execution
main() {
    echo "Starting PyTorch compilation for Intel Xeon E5 v2 + RTX 3060..."
    echo ""

    check_requirements
    install_dependencies
    compile_pytorch
    test_installation
    create_env_setup

    echo "=== Compilation Complete! ==="
    echo ""
    echo "To use PyTorch, source the environment script:"
    echo "source $BUILD_DIR/setup-pytorch-env.sh"
    echo ""
    echo "PyTorch is now configured for your Intel Xeon E5 v2 processor with RTX 3060 GPU support."
}

# Run main function
main "$@"