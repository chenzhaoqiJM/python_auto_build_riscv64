#!/usr/bin/env bash
# PYMUPDF_env.sh
# 用法: source PYMUPDF_env.sh <action>

# 维护激活状态
: "${_PYMUPDF_ENV_ACTIVE:=0}"


if [[ "$1" == "activate" ]]; then

    if [[ "$2" != pymupdf* ]]; then
        echo "[PYMUPDFEnv] Skip: package '$2' is not PYMUPDF, no environment change"
        return 0
    fi

    if [[ "$_PYMUPDF_ENV_ACTIVE" -eq 1 ]]; then
        echo "[PYMUPDFEnv] Warning: PYMUPDF environment already active, skipping activate"
        return 0
    fi

    local llvmlib_PREFIX="/usr/lib/llvm-18"

    echo "[PYMUPDFEnv] Activating PYMUPDF environment, DIR = $llvmlib_PREFIX"

    # 备份原有环境变量
    export _PYMUPDF_ENV_OLD_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"

    export LD_LIBRARY_PATH="${llvmlib_PREFIX}/lib:${LD_LIBRARY_PATH}"

    _PYMUPDF_ENV_ACTIVE=1

elif [[ "$1" == "deactivate" ]]; then
    if [[ "$_PYMUPDF_ENV_ACTIVE" -eq 0 ]]; then
        echo "[PYMUPDFEnv] PYMUPDF environment not active, skipping deactivate"
        return 0
    fi

    echo "[PYMUPDFEnv] Restoring environment"

    # 恢复原有环境变量
    if [[ -n "${_PYMUPDF_ENV_OLD_LD_LIBRARY_PATH:-}" ]]; then
        export LD_LIBRARY_PATH="$_PYMUPDF_ENV_OLD_LD_LIBRARY_PATH"
        unset _PYMUPDF_ENV_OLD_LD_LIBRARY_PATH
    fi


    _PYMUPDF_ENV_ACTIVE=0
    echo "[PYMUPDFEnv] UNSET OK, Now LD_LIBRARY_PATH == $LD_LIBRARY_PATH"

else
    echo "Usage: source PYMUPDF_env.sh activate"
    echo "       source PYMUPDF_env.sh deactivate"
fi
