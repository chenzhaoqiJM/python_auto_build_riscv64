#!/usr/bin/env bash
# opencv_env.sh
# 用法: source opencv_env.sh <action> <package>

# 维护激活状态
: "${_opencv_ENV_ACTIVE:=0}"

# 公共环境变量
source "$SCRIPT_DIR_ENV_LOADER/../common_func.sh"

# 根据包名选择 opencv 安装路径
get_opencv_prefix_by_pkg() {
    local pkg="$1"
    if [ -z "$pkg" ]; then
        echo "Usage: get_opencv_prefix_by_pkg <package>"
        return 1
    fi

    # 拆分包名
    IFS='=' read -r name _ version <<< "$pkg"

    # 默认版本
    local default_version="4.13.0.90"

    # 如果不是 opencv 或版本缺失，使用默认版本
    if [[ "$name" != opencv* ]] || [ -z "$version" ]; then
        version="$default_version"
    fi

    echo "$version"
}

# 比较版本大小函数，返回0表示 v1 <= v2
version_le() {
    # 将版本按点分割成数组
    IFS='.' read -r -a ver1 <<< "$1"
    IFS='.' read -r -a ver2 <<< "$2"

    for i in {0..3}; do
        # 如果某段缺失，视为0
        v1=${ver1[i]:-0}
        v2=${ver2[i]:-0}
        if (( v1 < v2 )); then
            return 0
        elif (( v1 > v2 )); then
            return 1
        fi
    done
    return 0  # 完全相等也视作 <=
}

if [[ "$1" == "activate" ]]; then

    if [[ "$2" != opencv* ]]; then
        echo "[opencvEnv] Skip: package '$2' is not opencv, no environment change"
        return 0
    fi

    pkg="$2"
    opencv_version=$(get_opencv_prefix_by_pkg "$pkg")

    # 根据 opencv 版本决定 Qt 安装路径
    if [[ "$opencv_version" == "4.13.0.90" ]]; then
        _opencv_INSTALL_PREFIX=/opt/Qt5.15.18
    elif [[ "$opencv_version" == "4.13.0.92" ]]; then
        _opencv_INSTALL_PREFIX=/opt/Qt5.15.18
    elif version_le "$opencv_version" "4.12.0.88"; then
        _opencv_INSTALL_PREFIX=/opt/Qt5.15.16
    else
        _opencv_INSTALL_PREFIX=/opt/Qt5.15.16  # 默认路径
    fi
    echo "[opencvEnv] opencv version: $opencv_version, using Qt path: $_opencv_INSTALL_PREFIX"

    if [[ -z "$_opencv_INSTALL_PREFIX" ]]; then
        echo "[opencvEnv] No opencv path configured for package: $pkg"
        _opencv_ENV_ACTIVE=0
        return 0
    fi

    if [[ "$_opencv_ENV_ACTIVE" -eq 1 ]]; then
        echo "[opencvEnv] Warning: opencv environment already active, skipping activate"
        return 0
    fi

    echo "[opencvEnv] Activating for package: $pkg" DIR TO $_opencv_INSTALL_PREFIX
    # export _opencv_ENV_OLD_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
    # export LD_LIBRARY_PATH="${_opencv_INSTALL_PREFIX}/lib:${LD_LIBRARY_PATH}"

    # 激活时保存
    export _opencv_ENV_OLD_LD_LIBRARY_PATH="${LD_LIBRARY_PATH-}"   # 即使为空也保存
    export LD_LIBRARY_PATH="${_opencv_INSTALL_PREFIX}/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

    export _opencv_ENV_OLD_PATH="$PATH"
    export PATH="${_opencv_INSTALL_PREFIX}/bin:${PATH}"

    echo "[opencvEnv] LD_LIBRARY_PATH : $LD_LIBRARY_PATH"
    echo "[opencvEnv] PATH : $PATH"

    # 方法1: 推荐使用 command -v
    if command -v qmake >/dev/null 2>&1; then
        echo "[opencvEnv] qmake found at: $(command -v qmake)"
    else
        echo "[opencvEnv] qmake not found"
    fi

    # 判断 Python 版本，>= 3.10 则禁用 LIMITED_API
    PYTHON_LIMITED_API=ON

    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
    if [[ -n "$python_version" ]]; then
        major=$(echo "$python_version" | cut -d. -f1)
        minor=$(echo "$python_version" | cut -d. -f2)
        if (( major > 3 || (major == 3 && minor >= 10) )); then
            echo "[opencvEnv] Python version $python_version >= 3.10, disabling LIMITED_API"
            PYTHON_LIMITED_API=OFF
        fi
    fi

    # 根据版本设置 CMAKE_ARGS
    if version_le "$opencv_version" "4.10.0.84"; then
        export CMAKE_ARGS="-Wno-error -DWITH_GTK=OFF -DWITH_QT=ON -DWITH_GTK_2_X=OFF -DPYTHON3_LIMITED_API=${PYTHON_LIMITED_API}"
    else
        export CMAKE_ARGS="-DCMAKE_CXX_FLAGS=-march=rv64gcv -DCMAKE_C_FLAGS=-march=rv64gcv -Wno-error -DWITH_GTK=OFF -DWITH_QT=ON -DWITH_GTK_2_X=OFF -DPYTHON3_LIMITED_API=${PYTHON_LIMITED_API}"
    fi

    export QTDIR=$_opencv_INSTALL_PREFIX
    echo "[opencvEnv] QTDIR = $QTDIR"

    _opencv_ENV_ACTIVE=1

    echo "[opencvEnv] CMAKE_ARGS=$CMAKE_ARGS"
    echo "[opencvEnv] Activated for $pkg (version $opencv_version) done!"


elif [[ "$1" == "deactivate" ]]; then
    if [[ "$_opencv_ENV_ACTIVE" -eq 0 ]]; then
        echo "[opencvEnv] opencv environment not active, skipping deactivate"
        return 0
    fi

    echo "[opencvEnv] Restoring environment"


    # 关闭时恢复
    if [[ "${_opencv_ENV_OLD_LD_LIBRARY_PATH+set}" == set ]]; then
        if [[ -n "$_opencv_ENV_OLD_LD_LIBRARY_PATH" ]]; then
            export LD_LIBRARY_PATH="$_opencv_ENV_OLD_LD_LIBRARY_PATH"
        else
            unset LD_LIBRARY_PATH
        fi
        unset _opencv_ENV_OLD_LD_LIBRARY_PATH
    fi


    if [[ -n "${_opencv_ENV_OLD_PATH:-}" ]]; then
        export PATH="$_opencv_ENV_OLD_PATH"
        unset _opencv_ENV_OLD_PATH
    fi

    unset CMAKE_ARGS

    unset QTDIR

    _opencv_ENV_ACTIVE=0

    echo "[opencvEnv] Deactivated. Now LD_LIBRARY_PATH == $LD_LIBRARY_PATH"
    echo "[opencvEnv] Deactivated. Now PATH == $PATH"

else
    echo "Usage: source opencv_env.sh activate <package>"
    echo "       source opencv_env.sh deactivate"
fi
