#!/usr/bin/env bash
# pyqt6_env.sh
# 用法: source pyqt6_env.sh <action> <package>

# 要设置的组件

# 维护激活状态
: "${_pyqt6_ENV_ACTIVE:=0}"


if [[ "$1" == "activate" ]]; then

    pkg_lower="${2,,}"
    if [[ "$pkg_lower" != pyqt6* && "$pkg_lower" != pyside6* && "$pkg_lower" != pyside-setup* ]]; then
        echo "[pyqt6Env] Skip: package '$2' does not use Qt6, no environment change"
        return 0
    fi

    local pkg="$2"
    pyqt6_INSTALL_PREFIX="${QT_INSTALL_PREFIX:-}"

    if [[ -z "$pyqt6_INSTALL_PREFIX" ]]; then
        echo "[pyqt6Env] QT_INSTALL_PREFIX is required for package: $pkg"
        _pyqt6_ENV_ACTIVE=0
        return 1
    fi

    if [[ "$_pyqt6_ENV_ACTIVE" -eq 1 ]]; then
        echo "[pyqt6Env] Warning: pyqt6 environment already active, skipping activate"
        return 0
    fi

    echo "[pyqt6Env] Activating for package: $pkg" DIR TO $pyqt6_INSTALL_PREFIX
    export _pyqt6_ENV_OLD_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
    export LD_LIBRARY_PATH="${pyqt6_INSTALL_PREFIX}/lib:${LD_LIBRARY_PATH}"

    export _pyqt6_ENV_OLD_PATH="$PATH"
    export PATH="${pyqt6_INSTALL_PREFIX}/bin:${PATH}"

    export _pyqt6_ENV_OLD_QTDIR="${QTDIR-}"
    export QTDIR="$pyqt6_INSTALL_PREFIX"

    echo "[pyqt6Env] PATH is: $PATH"

    # 方法1: 推荐使用 command -v
    if command -v qmake >/dev/null 2>&1; then
        echo "[pyqt6Env] qmake found at: $(command -v qmake)"
    else
        echo "[pyqt6Env] qmake not found"
    fi

    _pyqt6_ENV_ACTIVE=1

elif [[ "$1" == "deactivate" ]]; then
    if [[ "$_pyqt6_ENV_ACTIVE" -eq 0 ]]; then
        echo "[pyqt6Env] pyqt6 environment not active, skipping deactivate"
        return 0
    fi

    echo "[pyqt6Env] Restoring environment"
    if [[ -n "${_pyqt6_ENV_OLD_LD_LIBRARY_PATH:-}" ]]; then
        export LD_LIBRARY_PATH="$_pyqt6_ENV_OLD_LD_LIBRARY_PATH"
        unset _pyqt6_ENV_OLD_LD_LIBRARY_PATH
    fi

    if [[ -n "${_pyqt6_ENV_OLD_PATH:-}" ]]; then
        export PATH="$_pyqt6_ENV_OLD_PATH"
        unset _pyqt6_ENV_OLD_PATH
    fi

    if [[ -n "${_pyqt6_ENV_OLD_QTDIR+x}" ]]; then
        if [[ -n "$_pyqt6_ENV_OLD_QTDIR" ]]; then
            export QTDIR="$_pyqt6_ENV_OLD_QTDIR"
        else
            unset QTDIR
        fi
        unset _pyqt6_ENV_OLD_QTDIR
    fi
    
    _pyqt6_ENV_ACTIVE=0
    echo "[pyqt6Env] UNSET OK, Now LD_LIBRARY_PATH == $LD_LIBRARY_PATH"

else
    echo "Usage: source pyqt6_env.sh activate <package>"
    echo "       source pyqt6_env.sh deactivate"
fi
