#!/usr/bin/env bash

: "${_STAG_PYTHON_ENV_ACTIVE:=0}"

stag_python_matches() {
    local pkg="$1"
    [[ "$pkg" == "stag-python" || "$pkg" == stag-python==* ]]
}

activate_stag_python_env() {
    local qt_root="/opt/Qt5.15.16"
    local qt_lib="$qt_root/lib"
    local qt_bin="$qt_root/bin"

    export _OLD_STAG_PYTHON_LD_LIBRARY_PATH="${LD_LIBRARY_PATH-}"
    export _OLD_STAG_PYTHON_PATH="${PATH-}"
    export _OLD_STAG_PYTHON_QTDIR="${QTDIR-}"
    export _OLD_STAG_PYTHON_CMAKE_ARGS="${CMAKE_ARGS-}"
    export _OLD_STAG_PYTHON_CI_BUILD="${CI_BUILD-}"
    export _OLD_STAG_PYTHON_MAKEFLAGS="${MAKEFLAGS-}"
    export _OLD_STAG_PYTHON_NINJAFLAGS="${NINJAFLAGS-}"

    if [[ ":${LD_LIBRARY_PATH-}:" != *":$qt_lib:"* ]]; then
        export LD_LIBRARY_PATH="$qt_lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    fi

    if [[ ":${PATH-}:" != *":$qt_bin:"* ]]; then
        export PATH="$qt_bin${PATH:+:$PATH}"
    fi

    export QTDIR="$qt_root"
    export CMAKE_ARGS="-Wno-error -DWITH_GTK=OFF -DWITH_QT=ON -DWITH_GTK_2_X=OFF"
    export CI_BUILD=1
    export MAKEFLAGS='-j8'
    export NINJAFLAGS='-j8'
    _STAG_PYTHON_ENV_ACTIVE=1

    echo "[INFO] stag-python env activated"
    echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"
    echo "QTDIR=${QTDIR}"
}

deactivate_stag_python_env() {
    if [[ "${_STAG_PYTHON_ENV_ACTIVE:-0}" -eq 0 ]]; then
        echo "[INFO] stag-python env not active, skipping deactivate"
        return 0
    fi

    export LD_LIBRARY_PATH="${_OLD_STAG_PYTHON_LD_LIBRARY_PATH-}"
    export PATH="${_OLD_STAG_PYTHON_PATH-}"

    if [[ -n "${_OLD_STAG_PYTHON_QTDIR+x}" ]]; then
        export QTDIR="${_OLD_STAG_PYTHON_QTDIR}"
    else
        unset QTDIR
    fi

    if [[ -n "${_OLD_STAG_PYTHON_CMAKE_ARGS+x}" ]]; then
        export CMAKE_ARGS="${_OLD_STAG_PYTHON_CMAKE_ARGS}"
    else
        unset CMAKE_ARGS
    fi

    if [[ -n "${_OLD_STAG_PYTHON_CI_BUILD+x}" ]]; then
        export CI_BUILD="${_OLD_STAG_PYTHON_CI_BUILD}"
    else
        unset CI_BUILD
    fi

    if [[ -n "${_OLD_STAG_PYTHON_MAKEFLAGS+x}" ]]; then
        export MAKEFLAGS="${_OLD_STAG_PYTHON_MAKEFLAGS}"
    else
        unset MAKEFLAGS
    fi

    if [[ -n "${_OLD_STAG_PYTHON_NINJAFLAGS+x}" ]]; then
        export NINJAFLAGS="${_OLD_STAG_PYTHON_NINJAFLAGS}"
    else
        unset NINJAFLAGS
    fi

    unset _OLD_STAG_PYTHON_LD_LIBRARY_PATH
    unset _OLD_STAG_PYTHON_PATH
    unset _OLD_STAG_PYTHON_QTDIR
    unset _OLD_STAG_PYTHON_CMAKE_ARGS
    unset _OLD_STAG_PYTHON_CI_BUILD
    unset _OLD_STAG_PYTHON_MAKEFLAGS
    unset _OLD_STAG_PYTHON_NINJAFLAGS
    _STAG_PYTHON_ENV_ACTIVE=0

    echo "[INFO] stag-python env deactivated"
}

case "$1" in
    activate)
        if stag_python_matches "$2"; then
            activate_stag_python_env
        fi
        ;;
    deactivate)
        deactivate_stag_python_env
        ;;
esac