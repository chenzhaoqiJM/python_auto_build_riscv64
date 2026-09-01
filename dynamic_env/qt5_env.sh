#!/usr/bin/env bash
# pyqt5_env.sh
# 用法: source pyqt5_env.sh <action> <package>

# 要设置的组件

# 维护激活状态
: "${_pyqt5_ENV_ACTIVE:=0}"


if [[ "$1" == "activate" ]]; then

    pkg_lower="${2,,}"
    if [[ "$pkg_lower" != pyqt5* && "$pkg_lower" != pyside2* ]]; then
        echo "[pyqt5Env] Skip: package '$2' does not use Qt5, no environment change"
        return 0
    fi

    local pkg="$2"
    pyqt5_INSTALL_PREFIX="${QT_INSTALL_PREFIX:-}"

    if [[ -z "$pyqt5_INSTALL_PREFIX" ]]; then
        echo "[pyqt5Env] QT_INSTALL_PREFIX is required for package: $pkg"
        _pyqt5_ENV_ACTIVE=0
        return 1
    fi

    if [[ "$_pyqt5_ENV_ACTIVE" -eq 1 ]]; then
        echo "[pyqt5Env] Warning: pyqt5 environment already active, skipping activate"
        return 0
    fi

    echo "[pyqt5Env] Activating for package: $pkg" DIR TO $pyqt5_INSTALL_PREFIX
    export _pyqt5_ENV_OLD_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
    export LD_LIBRARY_PATH="${pyqt5_INSTALL_PREFIX}/lib:${LD_LIBRARY_PATH}"

    export _pyqt5_ENV_OLD_PATH="$PATH"
    export PATH="${pyqt5_INSTALL_PREFIX}/bin:${PATH}"

    export _pyqt5_ENV_OLD_QTDIR="${QTDIR-}"
    export QTDIR="$pyqt5_INSTALL_PREFIX"

    echo "[pyqt5Env] PATH is: $PATH"

    # 方法1: 推荐使用 command -v
    if command -v qmake >/dev/null 2>&1; then
        echo "[pyqt5Env] qmake found at: $(command -v qmake)"
    else
        echo "[pyqt5Env] qmake not found"
    fi

    _pyqt5_ENV_ACTIVE=1

elif [[ "$1" == "deactivate" ]]; then
    if [[ "$_pyqt5_ENV_ACTIVE" -eq 0 ]]; then
        echo "[pyqt5Env] pyqt5 environment not active, skipping deactivate"
        return 0
    fi

    echo "[pyqt5Env] Restoring environment"
    if [[ -n "${_pyqt5_ENV_OLD_LD_LIBRARY_PATH:-}" ]]; then
        export LD_LIBRARY_PATH="$_pyqt5_ENV_OLD_LD_LIBRARY_PATH"
        unset _pyqt5_ENV_OLD_LD_LIBRARY_PATH
    fi

    if [[ -n "${_pyqt5_ENV_OLD_PATH:-}" ]]; then
        export PATH="$_pyqt5_ENV_OLD_PATH"
        unset _pyqt5_ENV_OLD_PATH
    fi

    if [[ -n "${_pyqt5_ENV_OLD_QTDIR+x}" ]]; then
        if [[ -n "$_pyqt5_ENV_OLD_QTDIR" ]]; then
            export QTDIR="$_pyqt5_ENV_OLD_QTDIR"
        else
            unset QTDIR
        fi
        unset _pyqt5_ENV_OLD_QTDIR
    fi
    
    _pyqt5_ENV_ACTIVE=0
    echo "[pyqt5Env] UNSET OK, Now LD_LIBRARY_PATH == $LD_LIBRARY_PATH"

else
    echo "Usage: source pyqt5_env.sh activate <package>"
    echo "       source pyqt5_env.sh deactivate"
fi
