#!/usr/bin/env bash
# MUJOCO_env.sh
# 用法: source MUJOCO_env.sh <action> <package>


# 维护激活状态
: "${_MUJOCO_ENV_ACTIVE:=0}"


if [[ "$1" == "activate" ]]; then

    if [[ "$2" != mujoco* ]]; then
        echo "[mujocoEnv] Skip: package '$2' is not mujoco, no environment change"
        return 0
    fi

    local pkg="$2"

    local name=$(echo "$pkg" | cut -d '=' -f1)
    local version=$(echo "$pkg" | cut -d '=' -f3)

    if echo "$pkg" | grep -q "mujoco"; then
        echo "包含 mujoco, 设置对应版本库 --------------------------------"
        if [ "$version" = "$name" ]; then
            echo "！！！注意：未传入版本，设置默认版本 3.3.5"
            version="3.3.5"
        else
            echo "收到 mujoco 正常版本"
        fi
    else
        echo "不包含 mujoco ，设置一个默认值 ---------------------"
        version="3.3.5"
    fi

    echo "mujoco version=$version"

    local MUJOCO_INSTALL_PREFIX="/opt/ext/mujoco/mujoco-$version"

    if [[ -z "$MUJOCO_INSTALL_PREFIX" ]]; then
        echo "[MUJOCOEnv] No MUJOCO path configured for package: $pkg"
        _MUJOCO_ENV_ACTIVE=0
        return 0
    fi

    if [[ "$_MUJOCO_ENV_ACTIVE" -eq 1 ]]; then
        echo "[MUJOCOEnv] Warning: MUJOCO environment already active, skipping activate"
        return 0
    fi

    echo "[MUJOCOEnv] Activating for package: $pkg" DIR TO $MUJOCO_INSTALL_PREFIX
    export _MUJOCO_ENV_OLD_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
    export LD_LIBRARY_PATH="${MUJOCO_INSTALL_PREFIX}/lib:${LD_LIBRARY_PATH}"
   
    export MUJOCO_PLUGIN_PATH="$MUJOCO_INSTALL_PREFIX/mujoco_plugin/"
    # export MUJOCO_CMAKE_ARGS="-DCMAKE_INTERPROCEDURAL_OPTIMIZATION:BOOL=OFF"
    # export MUJOCO_CMAKE_ARGS="-DCMAKE_INTERPROCEDURAL_OPTIMIZATION:BOOL=OFF -G Ninja -DCMAKE_C_COMPILER=gcc-14 -DCMAKE_CXX_COMPILER=g++-14 -DCMAKE_EXE_LINKER_FLAGS=-Wl,--no-as-needed"
    export MUJOCO_CMAKE_ARGS="-DCMAKE_INTERPROCEDURAL_OPTIMIZATION:BOOL=OFF -G Ninja -DCMAKE_C_COMPILER:STRING=clang-18 -DCMAKE_CXX_COMPILER:STRING=clang++-18 -DCMAKE_EXE_LINKER_FLAGS:STRING=-fuse-ld=lld -DMUJOCO_HARDEN:BOOL=ON"

    export MUJOCO_PATH="$MUJOCO_INSTALL_PREFIX"
    
    _MUJOCO_ENV_ACTIVE=1

elif [[ "$1" == "deactivate" ]]; then
    if [[ "$_MUJOCO_ENV_ACTIVE" -eq 0 ]]; then
        echo "[MUJOCOEnv] MUJOCO environment not active, skipping deactivate"
        return 0
    fi

    echo "[MUJOCOEnv] Restoring environment"
    if [[ -n "${_MUJOCO_ENV_OLD_LD_LIBRARY_PATH:-}" ]]; then
        export LD_LIBRARY_PATH="$_MUJOCO_ENV_OLD_LD_LIBRARY_PATH"
        unset _MUJOCO_ENV_OLD_LD_LIBRARY_PATH
    fi
    
    _MUJOCO_ENV_ACTIVE=0
    echo MUJOCO ENV UNSET OK, Now LD_LIBRARY_PATH == $LD_LIBRARY_PATH

else
    echo "Usage: source MUJOCO_env.sh activate <package>"
    echo "       source MUJOCO_env.sh deactivate"
fi
