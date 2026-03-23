#!/usr/bin/env bash
# av_env.sh
# 用法: source av_env.sh <action>

# 维护激活状态
: "${_AV_ENV_ACTIVE:=0}"

# FFmpeg 安装前缀
_AV_FFMPEG_PREFIX="/opt/ext/ffmpeg/ffmpeg-n7.0.2"
# _AV_FFMPEG_PREFIX=" /usr/lib/riscv64-linux-gnu"

if [[ "$1" == "activate" ]]; then

    if [[ "$2" != av* ]]; then
        echo "[AvEnv] Skip: package '$2' is not av, no environment change"
        return 0
    fi

    if [[ "$_AV_ENV_ACTIVE" -eq 1 ]]; then
        echo "[AvEnv] Warning: AV environment already active, skipping activate"
        return 0
    fi

    echo "[AvEnv] Activating AV environment, DIR = $_AV_FFMPEG_PREFIX"

    # 备份原有环境变量
    export _AV_ENV_OLD_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
    export _AV_ENV_OLD_PKG_CONFIG_PATH="$PKG_CONFIG_PATH"

    # 注入 FFmpeg 的路径
    export PKG_CONFIG_PATH="${_AV_FFMPEG_PREFIX}/lib/pkgconfig:${PKG_CONFIG_PATH}"
    export LD_LIBRARY_PATH="${_AV_FFMPEG_PREFIX}/lib:${LD_LIBRARY_PATH}"

    _AV_ENV_ACTIVE=1

elif [[ "$1" == "deactivate" ]]; then
    if [[ "$_AV_ENV_ACTIVE" -eq 0 ]]; then
        echo "[AvEnv] AV environment not active, skipping deactivate"
        return 0
    fi

    echo "[AvEnv] Restoring environment"

    # 恢复原有环境变量
    if [[ -n "${_AV_ENV_OLD_LD_LIBRARY_PATH:-}" ]]; then
        export LD_LIBRARY_PATH="$_AV_ENV_OLD_LD_LIBRARY_PATH"
        unset _AV_ENV_OLD_LD_LIBRARY_PATH
    fi

    if [[ -n "${_AV_ENV_OLD_PKG_CONFIG_PATH:-}" ]]; then
        export PKG_CONFIG_PATH="$_AV_ENV_OLD_PKG_CONFIG_PATH"
        unset _AV_ENV_OLD_PKG_CONFIG_PATH
    fi

    _AV_ENV_ACTIVE=0
    echo "[AvEnv] UNSET OK, Now LD_LIBRARY_PATH == $LD_LIBRARY_PATH"

else
    echo "Usage: source av_env.sh activate"
    echo "       source av_env.sh deactivate"
fi
