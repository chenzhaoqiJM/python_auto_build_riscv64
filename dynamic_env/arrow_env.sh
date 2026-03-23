#!/usr/bin/env bash
# arrow_env.sh
# 用法: source arrow_env.sh <action> <package>

# 要设置的组件
ARROW_COMPONENTS=(Arrow ArrowSubstrait ArrowAcero ArrowCompute ArrowDataset Parquet)

# 维护激活状态
: "${_ARROW_ENV_ACTIVE:=0}"

# 根据包名选择 Arrow 安装路径
get_arrow_prefix_by_pkg() {
    local pkg="$1"
    if [ -z "$pkg" ]; then
        echo "Usage: get_arrow_prefix_by_pkg <package>"
        return 1
    fi

    # 拆分包名
    IFS='=' read -r name _ version <<< "$pkg"

    # 默认版本
    local default_version="21.0.0"

    # 如果不是 pyarrow 或版本缺失，使用默认版本
    if [[ "$name" != "pyarrow" ]] || [ -z "$version" ]; then
        version="$default_version"
    fi

    local install_prefix="/opt/ext/arrow/apache-arrow-$version"
    echo "$install_prefix"
}

if [[ "$1" == "activate" ]]; then

    if [[ "$2" != pyarrow* ]]; then
        echo "[pyarrowEnv] Skip: package '$2' is not pyarrow, no environment change"
        return 0
    fi

    pkg="$2"
    ARROW_INSTALL_PREFIX=$(get_arrow_prefix_by_pkg "$pkg")

    if [[ -z "$ARROW_INSTALL_PREFIX" ]]; then
        echo "[ArrowEnv] No Arrow path configured for package: $pkg"
        _ARROW_ENV_ACTIVE=0
        return 0
    fi

    if [[ "$_ARROW_ENV_ACTIVE" -eq 1 ]]; then
        echo "[ArrowEnv] Warning: Arrow environment already active, skipping activate"
        return 0
    fi

    echo "[ArrowEnv] Activating for package: $pkg" DIR TO $ARROW_INSTALL_PREFIX
    export _ARROW_ENV_OLD_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
    export LD_LIBRARY_PATH="${ARROW_INSTALL_PREFIX}/lib:${LD_LIBRARY_PATH}"
    for dir in "${ARROW_COMPONENTS[@]}"; do
        export ${dir}_DIR="${ARROW_INSTALL_PREFIX}"
    done
    _ARROW_ENV_ACTIVE=1

elif [[ "$1" == "deactivate" ]]; then
    if [[ "$_ARROW_ENV_ACTIVE" -eq 0 ]]; then
        echo "[ArrowEnv] Arrow environment not active, skipping deactivate"
        return 0
    fi

    echo "[ArrowEnv] Restoring environment"
    if [[ -n "${_ARROW_ENV_OLD_LD_LIBRARY_PATH:-}" ]]; then
        export LD_LIBRARY_PATH="$_ARROW_ENV_OLD_LD_LIBRARY_PATH"
        unset _ARROW_ENV_OLD_LD_LIBRARY_PATH
    fi
    for dir in "${ARROW_COMPONENTS[@]}"; do
        unset ${dir}_DIR
    done
    _ARROW_ENV_ACTIVE=0
    echo ArrowEnv UNSET OK, Now LD_LIBRARY_PATH == $LD_LIBRARY_PATH

else
    echo "Usage: source arrow_env.sh activate <package>"
    echo "       source arrow_env.sh deactivate"
fi
