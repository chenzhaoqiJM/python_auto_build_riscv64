#!/usr/bin/env bash
# cyclonedds_env.sh
# 用法: source cyclonedds_env.sh <action> <package>

# 要设置的组件

# 维护激活状态
: "${_cyclonedds_ENV_ACTIVE:=0}"

# 根据包名选择 Cyclonedds 安装路径
get_cyclonedds_prefix_by_pkg() {
    local pkg="$1"
    if [ -z "$pkg" ]; then
        echo "Usage: get_cyclonedds_prefix_by_pkg <package>"
        return 1
    fi

    # 拆分包名
    IFS='=' read -r name _ version <<< "$pkg"

    # 默认版本
    local default_version="0.10.5"

    # 如果不是 cyclonedds 或版本缺失，使用默认版本
    if [[ "$name" != "cyclonedds" ]] || [ -z "$version" ]; then
        version="$default_version"
    fi

    local install_prefix="/opt/ext/cyclonedds/cyclonedds-$version"
    echo "$install_prefix"
}

if [[ "$1" == "activate" ]]; then

    if [[ "$2" != cyclonedds* ]]; then
        echo "[cycloneddsEnv] Skip: package '$2' is not cyclonedds, no environment change"
        return 0
    fi

    pkg="$2"
    cyclonedds_INSTALL_PREFIX=$(get_cyclonedds_prefix_by_pkg "$pkg")

    if [[ -z "$cyclonedds_INSTALL_PREFIX" ]]; then
        echo "[cycloneddsEnv] No Cyclonedds path configured for package: $pkg"
        _cyclonedds_ENV_ACTIVE=0
        return 0
    fi

    if [[ "$_cyclonedds_ENV_ACTIVE" -eq 1 ]]; then
        echo "[cycloneddsEnv] Warning: Cyclonedds environment already active, skipping activate"
        return 0
    fi

    echo "[cycloneddsEnv] Activating for package: $pkg" DIR TO $cyclonedds_INSTALL_PREFIX
    export _cyclonedds_ENV_OLD_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
    export LD_LIBRARY_PATH="${cyclonedds_INSTALL_PREFIX}/lib:${LD_LIBRARY_PATH}"

    export CYCLONEDDS_HOME=$cyclonedds_INSTALL_PREFIX
    export STANDALONE_WHEELS=1

    _cyclonedds_ENV_ACTIVE=1

elif [[ "$1" == "deactivate" ]]; then
    if [[ "$_cyclonedds_ENV_ACTIVE" -eq 0 ]]; then
        echo "[cycloneddsEnv] Cyclonedds environment not active, skipping deactivate"
        return 0
    fi

    echo "[cycloneddsEnv] Restoring environment"
    if [[ -n "${_cyclonedds_ENV_OLD_LD_LIBRARY_PATH:-}" ]]; then
        export LD_LIBRARY_PATH="$_cyclonedds_ENV_OLD_LD_LIBRARY_PATH"
        unset _cyclonedds_ENV_OLD_LD_LIBRARY_PATH
    fi

    unset CYCLONEDDS_HOME
    unset STANDALONE_WHEELS
    
    _cyclonedds_ENV_ACTIVE=0
    echo cycloneddsEnv UNSET OK, Now LD_LIBRARY_PATH == $LD_LIBRARY_PATH

else
    echo "Usage: source cyclonedds_env.sh activate <package>"
    echo "       source cyclonedds_env.sh deactivate"
fi
