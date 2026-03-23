#!/usr/bin/env bash
# LLVM_LITE_env.sh
# 用法: source LLVM_LITE_env.sh <action> <package>


# 维护激活状态
: "${_LLVM_LITE_ENV_ACTIVE:=0}"

# 根据包名获取 LLVM 主版本号
_get_llvm_version_by_pkg() {
    case "$1" in
        "llvmlite==0.42.0"|"llvmlite==0.41.1"|"llvmlite==0.41.0"|"llvmlite==0.43.0")
            echo "14" ;;
        "llvmlite==0.44.0")
            echo "15" ;;
        "llvmlite==0.45.1"|"llvmlite==0.45.0"|"llvmlite==0.46.0")
            echo "20" ;;
        *)
            echo "19" ;;
    esac
}

# 根据包名选择 LLVM 安装路径
get_LLVM_LITE_prefix_by_pkg() {
    local ver
    ver=$(_get_llvm_version_by_pkg "$1")
    echo "/usr/bin/llvm-config-${ver}"
}

get_LLVM_CMake_prefix_by_pkg() {
    local ver
    ver=$(_get_llvm_version_by_pkg "$1")
    echo "/usr/lib/llvm-${ver}/cmake"
}

get_LLVM_Bin_prefix_by_pkg() {
    local ver
    ver=$(_get_llvm_version_by_pkg "$1")
    echo "/usr/lib/llvm-${ver}/bin"
}

if [[ "$1" == "activate" ]]; then
    pkg="$2"
    LLVM_LITE_CONFIG_PATH=$(get_LLVM_LITE_prefix_by_pkg "$pkg")
    LLVM_LITE_CMAKE_PATH=$(get_LLVM_CMake_prefix_by_pkg "$pkg")
    LLVM_LITE_BIN_PATH=$(get_LLVM_Bin_prefix_by_pkg "$pkg")

    if [[ -z "$LLVM_LITE_CONFIG_PATH" ]]; then
        echo "[LLVMEnv] No LLVM path configured for package: $pkg"
        _LLVM_LITE_ENV_ACTIVE=0
        return 0
    fi

    if [[ "$_LLVM_LITE_ENV_ACTIVE" -eq 1 ]]; then
        echo "[LLVMEnv] Warning: LLVM environment already active, skipping activate"
        return 0
    fi

    echo "[LLVMEnv] Activating for package: $pkg" DIR TO $LLVM_LITE_CONFIG_PATH and $LLVM_LITE_CMAKE_PATH
    export LLVM_CONFIG=$LLVM_LITE_CONFIG_PATH
    export LLVMLITE_SKIP_LLVM_VERSION_CHECK=1
    export LLVM_DIR=$LLVM_LITE_CMAKE_PATH

    # export CC=$LLVM_LITE_BIN_PATH/clang
    # export CXX=$LLVM_LITE_BIN_PATH/clang++
    # export CXX_FLTO_FLAGS=""
    # export LD_FLTO_FLAGS=-Wl

    _LLVM_LITE_ENV_ACTIVE=1

elif [[ "$1" == "deactivate" ]]; then
    if [[ "$_LLVM_LITE_ENV_ACTIVE" -eq 0 ]]; then
        echo "[LLVMEnv] LLVM environment not active, skipping deactivate"
        return 0
    fi

    # default
    export LLVM_CONFIG=/usr/bin/llvm-config-19
    export LLVM_DIR=/usr/lib/llvm-19/cmake

    unset LLVMLITE_SKIP_LLVM_VERSION_CHECK
    unset CC
    unset CXX
    unset CXX_FLTO_FLAGS
    unset LD_FLTO_FLAGS

    _LLVM_LITE_ENV_ACTIVE=0

else
    echo "Usage: source LLVM_LITE_env.sh activate <package>"
    echo "       source LLVM_LITE_env.sh deactivate"
fi
