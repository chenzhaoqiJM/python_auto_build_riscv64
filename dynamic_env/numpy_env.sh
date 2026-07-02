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
    export _ORIG_LDFLAGS="${LDFLAGS:-}"
    export _ORIG_PKG_CONFIG_PATH="${PKG_CONFIG_PATH:-}"
    export _ORIG_LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"
    export _ORIG_NPY_BLAS_ORDER="${NPY_BLAS_ORDER:-}"
    export _ORIG_NPY_LAPACK_ORDER="${NPY_LAPACK_ORDER:-}"

    # 设置优化编译选项
    export CFLAGS="-O3 -march=rv64gcv -ftree-vectorize -ffast-math"
    export CXXFLAGS="-O3 -march=rv64gcv -ftree-vectorize -ffast-math"
    export NPY_BLAS_ORDER=openblas
    export NPY_LAPACK_ORDER=openblas

    OPENBLAS_SPACEMIT_PREFIX="/opt/openblas-spacemit"
    if [[ -d "$OPENBLAS_SPACEMIT_PREFIX/lib/pkgconfig" && -d "$OPENBLAS_SPACEMIT_PREFIX/include" && -d "$OPENBLAS_SPACEMIT_PREFIX/lib" ]]; then
        export PKG_CONFIG_PATH="$OPENBLAS_SPACEMIT_PREFIX/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
        export LD_LIBRARY_PATH="$OPENBLAS_SPACEMIT_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
        export CFLAGS="-I$OPENBLAS_SPACEMIT_PREFIX/include $CFLAGS"
        export LDFLAGS="-L$OPENBLAS_SPACEMIT_PREFIX/lib -Wl,-rpath,$OPENBLAS_SPACEMIT_PREFIX/lib ${LDFLAGS:-}"
        echo "[numpyEnv] Using openblas-spacemit: $OPENBLAS_SPACEMIT_PREFIX"
    else
        echo "[numpyEnv] openblas-spacemit not found, using system OpenBLAS if available"
    fi

    echo "[numpyEnv] CFLAGS=$CFLAGS"
    echo "[numpyEnv] CXXFLAGS=$CXXFLAGS"
    echo "[numpyEnv] LDFLAGS=${LDFLAGS:-}"
    echo "[numpyEnv] PKG_CONFIG_PATH=${PKG_CONFIG_PATH:-}"

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
    export LDFLAGS="${_ORIG_LDFLAGS:-}"
    export PKG_CONFIG_PATH="${_ORIG_PKG_CONFIG_PATH:-}"
    export LD_LIBRARY_PATH="${_ORIG_LD_LIBRARY_PATH:-}"
    export NPY_BLAS_ORDER="${_ORIG_NPY_BLAS_ORDER:-}"
    export NPY_LAPACK_ORDER="${_ORIG_NPY_LAPACK_ORDER:-}"

    unset _ORIG_CFLAGS
    unset _ORIG_CXXFLAGS
    unset _ORIG_LDFLAGS
    unset _ORIG_PKG_CONFIG_PATH
    unset _ORIG_LD_LIBRARY_PATH
    unset _ORIG_NPY_BLAS_ORDER
    unset _ORIG_NPY_LAPACK_ORDER

    _NUMPY_ENV_ACTIVE=0
    echo "[numpyEnv] Environment deactivated"

fi
