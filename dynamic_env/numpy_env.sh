#!/usr/bin/env bash
# numpy_env.sh
# 用法: source numpy_env.sh <action> <package>


# 维护激活状态
: "${_NUMPY_ENV_ACTIVE:=0}"


if [[ "$1" == "activate" ]]; then

    if [[ "$2" != numpy* ]]; then
        echo "[numpyEnv] Skip: package '$2' is not numpy, no environment change"
        return 0
    fi

    if [[ $_NUMPY_ENV_ACTIVE -eq 1 ]]; then
        echo "[numpyEnv] Already activated, skipping"
        return 0
    fi

    echo "[numpyEnv] Activating numpy build environment..."

    # 保存原始环境变量
    export _ORIG_CFLAGS="${CFLAGS:-}"
    export _ORIG_CXXFLAGS="${CXXFLAGS:-}"

    # 设置优化编译选项
    export CFLAGS="-O3 -march=rv64gcv -ftree-vectorize -ffast-math"
    export CXXFLAGS="-O3 -march=rv64gcv -ftree-vectorize -ffast-math"

    echo "[numpyEnv] CFLAGS=$CFLAGS"
    echo "[numpyEnv] CXXFLAGS=$CXXFLAGS"

    _NUMPY_ENV_ACTIVE=1
    echo "[numpyEnv] Environment activated"


elif [[ "$1" == "deactivate" ]]; then

    if [[ $_NUMPY_ENV_ACTIVE -eq 0 ]]; then
        echo "[numpyEnv] Not activated, skipping deactivation"
        return 0
    fi

    echo "[numpyEnv] Deactivating numpy build environment..."

    # 恢复原始环境变量
    export CFLAGS="${_ORIG_CFLAGS:-}"
    export CXXFLAGS="${_ORIG_CXXFLAGS:-}"

    unset _ORIG_CFLAGS
    unset _ORIG_CXXFLAGS

    _NUMPY_ENV_ACTIVE=0
    echo "[numpyEnv] Environment deactivated"

fi
