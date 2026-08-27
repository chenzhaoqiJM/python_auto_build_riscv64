#!/usr/bin/env bash
# av_env.sh
# 用法: source av_env.sh <action>

# 维护激活状态
: "${_AV_ENV_ACTIVE:=0}"

_av_select_ffmpeg_tag() {
    local av_version="$1"
    local major minor patch

    if [[ ! "$av_version" =~ ^([0-9]+)\.([0-9]+)(\.([0-9]+))?([[:alnum:].+-]*)?$ ]]; then
        echo "[AvEnv] Error: unsupported av version '$av_version'" >&2
        return 1
    fi

    major="${BASH_REMATCH[1]}"
    minor="${BASH_REMATCH[2]}"
    patch="${BASH_REMATCH[4]:-0}"

    # 与 PyAV 各发布标签 scripts/activate.sh 的默认版本保持一致。
    case "$major" in
        7|8|9|10)
            echo "n4.2"
            ;;
        11)
            echo "n6.0"
            ;;
        12)
            if (( minor == 0 )); then
                echo "n6.0"
            else
                echo "n6.1.6"
            fi
            ;;
        13)
            if (( minor == 0 )); then
                echo "n7.0.2"
            else
                echo "n7.1.1"
            fi
            ;;
        14)
            if (( minor <= 2 )); then
                echo "n7.1.1"
            else
                echo "n7.1.1"
            fi
            ;;
        15)
            if (( minor == 0 )); then
                echo "n7.1.1"
            else
                echo "n8.0"
            fi
            ;;
        16)
            echo "n8.0"
            ;;
        17)
            if (( minor == 0 && patch == 0 )); then
                echo "n8.0.1"
            elif (( minor == 0 )); then
                echo "n8.1"
            else
                echo "n8.1.1"
            fi
            ;;
        18)
            echo "n8.1.2"
            ;;
        *)
            echo "[AvEnv] Error: no FFmpeg mapping for av==$av_version" >&2
            return 1
            ;;
    esac
}

if [[ "$1" == "activate" ]]; then

    if [[ "$2" != "av" && "$2" != av==* ]]; then
        echo "[AvEnv] Skip: package '$2' is not av, no environment change"
        return 0
    fi

    if [[ "$_AV_ENV_ACTIVE" -eq 1 ]]; then
        echo "[AvEnv] Warning: AV environment already active, skipping activate"
        return 0
    fi

    _AV_PACKAGE_VERSION="${2#av==}"
    if [[ "$2" == "av" ]]; then
        # PyPI 当前最新 PyAV 18.x 使用 FFmpeg 8.1.2。
        _AV_PACKAGE_VERSION="18.1.0"
    fi

    if ! _AV_FFMPEG_TAG="$(_av_select_ffmpeg_tag "$_AV_PACKAGE_VERSION")"; then
        return 1
    fi
    _AV_FFMPEG_PREFIX="/opt/ext/ffmpeg/ffmpeg-${_AV_FFMPEG_TAG}"

    echo "[AvEnv] Activating av==$_AV_PACKAGE_VERSION with FFmpeg $_AV_FFMPEG_TAG"
    echo "[AvEnv] FFmpeg DIR = $_AV_FFMPEG_PREFIX"

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
