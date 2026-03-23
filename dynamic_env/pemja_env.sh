#!/usr/bin/env bash
# pemja_env.sh
# 用法: source pemja_env.sh <action> <package>

# 要设置的组件

# 维护激活状态
: "${_pemja_ENV_ACTIVE:=0}"


if [[ "$1" == "activate" ]]; then

    if [[ "$2" != pemja* ]]; then
        echo "[pemjaEnv] Skip: package '$2' is not pemja, no environment change"
        return 0
    fi

    local pkg="$2"
    
    local pemja_INSTALL_PREFIX=/usr/lib/jvm/java-21-openjdk-riscv64
    

    if [[ -z "$pemja_INSTALL_PREFIX" ]]; then
        echo "[pemjaEnv] No pemja path configured for package: $pkg"
        _pemja_ENV_ACTIVE=0
        return 0
    fi

    if [[ "$_pemja_ENV_ACTIVE" -eq 1 ]]; then
        echo "[pemjaEnv] Warning: pemja environment already active, skipping activate"
        return 0
    fi

    echo "[pemjaEnv] Activating for package: $pkg" DIR TO $pemja_INSTALL_PREFIX
    export JAVA_HOME=$pemja_INSTALL_PREFIX

    export _pemja_ENV_OLD_PATH="$PATH"
    export PATH="${pemja_INSTALL_PREFIX}/bin:${PATH}"

    echo "[pemjaEnv] PATH is: $PATH"

    # 方法1: 推荐使用 command -v
    if command -v qmake >/dev/null 2>&1; then
        echo "[pemjaEnv] qmake found at: $(command -v qmake)"
    else
        echo "[pemjaEnv] qmake not found"
    fi

    _pemja_ENV_ACTIVE=1

elif [[ "$1" == "deactivate" ]]; then
    if [[ "$_pemja_ENV_ACTIVE" -eq 0 ]]; then
        echo "[pemjaEnv] pemja environment not active, skipping deactivate"
        return 0
    fi

    unset JAVA_HOME

    if [[ -n "${_pemja_ENV_OLD_PATH:-}" ]]; then
        export PATH="$_pemja_ENV_OLD_PATH"
        unset _pemja_ENV_OLD_PATH
    fi
    
    _pemja_ENV_ACTIVE=0
    echo "[pemjaEnv] UNSET OK, Now LD_LIBRARY_PATH == $LD_LIBRARY_PATH"

else
    echo "Usage: source pemja_env.sh activate <package>"
    echo "       source pemja_env.sh deactivate"
fi
