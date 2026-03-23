#!/usr/bin/env bash

# 维护激活状态
: "${_PYNACL_ENV_ACTIVE:=0}"

if [[ "$1" == "activate" ]]; then

    if [[ "$2" != PyNaCl* ]]; then
        echo "[PYNACL_Env] Skip: package '$2' is not PyNaCl, no environment change"
        return 0
    fi

    if [[ "$_PYNACL_ENV_ACTIVE" -eq 1 ]]; then
        echo "[PYNACL_Env] Warning: PyNaCl environment already active, skipping activate"
        return 0
    fi

    echo "[PyNaClEnv] Activating PyNaCl environment, LDFLAGS = empty"

    export _PyNaCl_ENV_OLD_LDFLAGS="$LDFLAGS"
    export LDFLAGS=""

    _PYNACL_ENV_ACTIVE=1

elif [[ "$1" == "deactivate" ]]; then
    if [[ "$_PYNACL_ENV_ACTIVE" -eq 0 ]]; then
        echo "[PYNACL_Env] PyNaCl environment not active, skipping deactivate"
        return 0
    fi

    echo "[PYNACL_Env] Restoring environment"

    export LDFLAGS="$_PyNaCl_ENV_OLD_LDFLAGS"
    unset _PyNaCl_ENV_OLD_LDFLAGS
    _PYNACL_ENV_ACTIVE=0
    echo "[PYNACL_Env] UNSET OK, Now LDFLAGS == $LDFLAGS"

else
    echo "Usage: source PyNaCl_env.sh activate"
    echo "       source PyNaCl_env.sh deactivate"
fi
