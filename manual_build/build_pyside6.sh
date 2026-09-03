#!/bin/bash
set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

INPUT_SOURCE=""
QT_DIR=""
SOURCE_DIR=""
BUILD_ROOT=""
WORK_DIR=""
PYTHON_REQUEST="${BUILD_FOR_VERSION:-3.12}"
VENV_DIR="$HOME/.cache/pyside6-build/venv-$PYTHON_REQUEST"
OUTPUT_DIR="${OUTPUT_DIR:-$HOME/whls/pyside6-wheelhouse}"
UPLOAD=0
KEEP_WORK=0
CHECK_ONLY=0

usage() {
    cat <<'EOF'
用法: build_pyside6.sh <pyside源码目录> <Qt安装目录> [选项]

脚本自动创建源码工作副本和 Python 虚拟环境，然后构建并后处理
pyside6、shiboken6 和 shiboken6_generator wheel。

选项:
  --check-only       创建/更新虚拟环境并检查输入，不构建
  --upload           构建成功后用 twine upload -r gitlab 上传三个 wheel
  --keep-work        成功后保留源码副本和后处理目录
  -h, --help         显示帮助

环境变量：
  BUILD_FOR_VERSION  Python 版本，默认 3.12
  OUTPUT_DIR         产物目录，默认 $HOME/whls/pyside6-wheelhouse
EOF
}

log() {
    printf '[%s] %s\n' "$(date '+%F %T')" "$*"
}

die() {
    printf '❌ %s\n' "$*" >&2
    exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi
[[ $# -ge 2 ]] || { usage >&2; die "必须指定 pyside 源码目录和 Qt 安装目录"; }
INPUT_SOURCE="$(cd "$1" 2>/dev/null && pwd -P)" || die "源码目录不存在: $1"
QT_DIR="$(cd "$2" 2>/dev/null && pwd -P)" || die "Qt 安装目录不存在: $2"
shift 2

while [[ $# -gt 0 ]]; do
    case "$1" in
        --check-only) CHECK_ONLY=1 ;;
        --upload) UPLOAD=1 ;;
        --keep-work) KEEP_WORK=1 ;;
        -h|--help) usage; exit 0 ;;
        *) die "未知参数: $1" ;;
    esac
    shift
done

[[ -f "$INPUT_SOURCE/setup.py" ]] || die "找不到 setup.py: $INPUT_SOURCE/setup.py"
[[ -f "$INPUT_SOURCE/requirements.txt" ]] || die "找不到 requirements.txt: $INPUT_SOURCE/requirements.txt"
for qt_part in bin lib plugins qml translations; do
    [[ -d "$QT_DIR/$qt_part" ]] || die "Qt 目录缺失: $QT_DIR/$qt_part"
done
[[ -f "$PROJECT_DIR/common_py/fix_whl/fix_whl_rpath.py" ]] || \
    die "找不到 wheel rpath 修复脚本: $PROJECT_DIR/common_py/fix_whl/fix_whl_rpath.py"

git_version="$(git -C "$INPUT_SOURCE" describe --tags --exact-match 2>/dev/null || true)"
[[ "$git_version" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+$ ]] || \
    die "源码必须位于正式版本 tag，当前为 ${git_version:-未命中 tag}"
VERSION="${git_version#v}"

mkdir -p "$(dirname "$VENV_DIR")"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    log "创建 Python $PYTHON_REQUEST 虚拟环境: $VENV_DIR"
    if command -v uv >/dev/null 2>&1; then
        uv venv "$VENV_DIR" --python "$PYTHON_REQUEST"
    else
        command -v "python$PYTHON_REQUEST" >/dev/null 2>&1 || \
            die "找不到 uv 或 python$PYTHON_REQUEST，无法创建虚拟环境"
        "python$PYTHON_REQUEST" -m venv "$VENV_DIR"
    fi
fi
PYTHON="$VENV_DIR/bin/python"

install_dependencies() {
    local attempt
    local -a extra_packages=(auditwheel)
    if [[ "$UPLOAD" -eq 1 ]]; then
        extra_packages+=(twine)
    fi
    for attempt in 1 2 3; do
        log "安装/更新构建依赖（第 $attempt 次）"
        if command -v uv >/dev/null 2>&1; then
            if uv pip install --python "$PYTHON" -r "$INPUT_SOURCE/requirements.txt" \
                "${extra_packages[@]}"; then
                return 0
            fi
        elif "$PYTHON" -m pip install -r "$INPUT_SOURCE/requirements.txt" \
            "${extra_packages[@]}"; then
            return 0
        fi
    done
    die "三次尝试后仍无法安装构建依赖"
}
install_dependencies

if command -v llvm-config-18 >/dev/null 2>&1; then
    LLVM_INSTALL_DIR="$(llvm-config-18 --prefix)"
elif command -v llvm-config >/dev/null 2>&1; then
    LLVM_INSTALL_DIR="$(llvm-config --prefix)"
else
    mapfile -t llvm_dirs < <(find /usr/lib -mindepth 1 -maxdepth 1 -type d \
        -name 'llvm-*' -print 2>/dev/null | sort -V)
    [[ ${#llvm_dirs[@]} -gt 0 ]] || die "找不到 LLVM 安装目录，请安装 libclang 和 clang"
    LLVM_INSTALL_DIR="${llvm_dirs[${#llvm_dirs[@]} - 1]}"
fi

export PATH="$VENV_DIR/bin:$QT_DIR/bin:$PATH"
export LD_LIBRARY_PATH="$QT_DIR/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LLVM_INSTALL_DIR QT_INSTALL_PREFIX="$QT_DIR" QTDIR="$QT_DIR"
export PACKAGE_NAME_REAL="pyside6==$VERSION"

PY_TAG="$($PYTHON -c 'from packaging.tags import sys_tags; print(next(sys_tags()).interpreter)')"
PLATFORM_TAG="linux_$(uname -m)"
TARGET_TAG="$PY_TAG-abi3-$PLATFORM_TAG"

for command_name in wheel auditwheel patchelf; do
    command -v "$command_name" >/dev/null 2>&1 || die "缺少命令: $command_name"
done
if [[ "$UPLOAD" -eq 1 ]]; then
    command -v twine >/dev/null 2>&1 || die "--upload 需要 twine"
fi

log "输入源码: $INPUT_SOURCE ($git_version)"
log "Python: $($PYTHON --version 2>&1)，目标 tag: $TARGET_TAG"
log "Qt: $QT_DIR，LLVM: $LLVM_INSTALL_DIR"

if [[ "$CHECK_ONLY" -eq 1 ]]; then
    "$PYTHON" -c 'import wheel, auditwheel, packaging'
    log "✅ 环境检查通过"
    exit 0
fi

[[ -d "$LLVM_INSTALL_DIR" ]] || die "LLVM 目录不存在: $LLVM_INSTALL_DIR"
mkdir -p "$HOME/.mytmp" "$OUTPUT_DIR"
BUILD_ROOT="$(mktemp -d "$HOME/.mytmp/pyside6-build.XXXXXXXX")"
SOURCE_DIR="$BUILD_ROOT/pyside-pyside-setup"
WORK_DIR="$BUILD_ROOT/postprocess"

cleanup() {
    local exit_code=$?
    if [[ $exit_code -eq 0 && "$KEEP_WORK" -eq 0 && -n "$BUILD_ROOT" && -d "$BUILD_ROOT" ]]; then
        rm -rf -- "${BUILD_ROOT:?}"
    elif [[ -n "$BUILD_ROOT" && -d "$BUILD_ROOT" ]]; then
        log "保留隔离工作目录便于排查: $BUILD_ROOT"
    fi
    exit "$exit_code"
}
trap cleanup EXIT

log "复制源码到隔离工作目录: $SOURCE_DIR"
mkdir -p "$SOURCE_DIR"
cp -a "$INPUT_SOURCE/." "$SOURCE_DIR/"
for generated_path in build dist PySide6.egg-info shiboken6.egg-info shiboken6_generator.egg-info; do
    if [[ -e "$SOURCE_DIR/$generated_path" ]]; then
        rm -rf -- "${SOURCE_DIR:?}/$generated_path"
    fi
done

log "从头构建三个原始 wheel"
(
    cd "$SOURCE_DIR"
    "$PYTHON" setup.py bdist_wheel
)

find_raw_wheel() {
    local package_name="$1"
    local -a matches=()
    mapfile -t matches < <(
        find "$SOURCE_DIR/dist" -maxdepth 1 -type f \
            -name "${package_name}-${VERSION}-*-${PY_TAG}-${PY_TAG}-${PLATFORM_TAG}.whl" \
            -printf '%T@ %p\n' | sort -rn | cut -d' ' -f2-
    )
    [[ ${#matches[@]} -gt 0 ]] || die "找不到 ${package_name} 的原始 wheel"
    printf '%s\n' "${matches[0]}"
}

PYSIDE_RAW="$(find_raw_wheel pyside6)"
SHIBOKEN_RAW="$(find_raw_wheel shiboken6)"
GENERATOR_RAW="$(find_raw_wheel shiboken6_generator)"

mkdir -p "$WORK_DIR"
log "后处理目录: $WORK_DIR"

unpack_wheel() {
    local wheel_path="$1"
    local destination="$2"
    mkdir -p "$destination"
    wheel unpack "$wheel_path" -d "$destination" >/dev/null
    find "$destination" -mindepth 1 -maxdepth 1 -type d -print -quit
}

set_wheel_tag() {
    local unpacked_dir="$1"
    local wheel_file
    wheel_file="$(find "$unpacked_dir" -maxdepth 2 -type f -path '*.dist-info/WHEEL' -print -quit)"
    [[ -n "$wheel_file" ]] || die "找不到 WHEEL 元数据: $unpacked_dir"
    "$PYTHON" - "$wheel_file" "$TARGET_TAG" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
tag = sys.argv[2]
lines = path.read_text(encoding="utf-8").splitlines()
tag_lines = [index for index, line in enumerate(lines) if line.startswith("Tag:")]
if not tag_lines:
    raise SystemExit(f"WHEEL 元数据中没有 Tag: {path}")
lines[tag_lines[0]] = f"Tag: {tag}"
lines = [line for index, line in enumerate(lines) if not line.startswith("Tag:") or index == tag_lines[0]]
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

pack_wheel() {
    local unpacked_dir="$1"
    local destination="$2"
    mkdir -p "$destination"
    wheel pack "$unpacked_dir" -d "$destination" >/dev/null || return 1
    local packed_wheel
    packed_wheel="$(find "$destination" -maxdepth 1 -type f \
        -name "*-${TARGET_TAG}.whl" -print -quit)"
    [[ -n "$packed_wheel" ]] || die "wheel pack 未生成目标 wheel: $unpacked_dir"
    printf '%s\n' "$packed_wheel"
}

fix_embedded_rpaths() {
    local wheel_path="$1"
    "$PYTHON" "$PROJECT_DIR/common_py/fix_whl/fix_whl_rpath.py" "$wheel_path"
}

repair_pyside6() {
    local unpacked_dir pyside_dir packed_wheel repaired_wheel
    unpacked_dir="$(unpack_wheel "$PYSIDE_RAW" "$WORK_DIR/pyside6-unpack")"
    pyside_dir="$unpacked_dir/PySide6"
    [[ -d "$pyside_dir" ]] || die "PySide6 包目录不存在: $pyside_dir"

    log "修复 PySide6 扩展模块 rpath"
    PYTHONPATH="$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" - "$pyside_dir" <<'PY'
from pathlib import Path
import sys
from common_py.fix_whl.fix_rpath_common import patch_rpath_all

root = Path(sys.argv[1])
rpath = "$ORIGIN/:$ORIGIN/Qt/lib:$ORIGIN/../shiboken6/"
patch_rpath_all(root=root, pattern="*.so", new_rpath=rpath)
patch_rpath_all(root=root, pattern="*.so.*", new_rpath=rpath)
PY

    log "复制 Qt 运行库、插件、QML 和翻译文件"
    mkdir -p "$pyside_dir/Qt"
    cp -a "$QT_DIR/lib" "$QT_DIR/plugins" "$QT_DIR/qml" "$QT_DIR/translations" \
        "$pyside_dir/Qt/"
    find "$pyside_dir/Qt/lib" -maxdepth 1 -type f -name '*.prl' -delete

    "$PYTHON" - "$pyside_dir/__init__.py" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
setting = 'os.environ["QT_QPA_PLATFORM"] = "wayland"'
if setting not in text:
    marker = 'SKIP_MYPY_TEST = bool("")\n'
    if marker not in text:
        raise SystemExit(f"无法定位 QT_QPA_PLATFORM 插入位置: {path}")
    text = text.replace(marker, marker + "\n" + setting + "\n", 1)
    path.write_text(text, encoding="utf-8")
PY
    set_wheel_tag "$unpacked_dir"
    packed_wheel="$(pack_wheel "$unpacked_dir" "$WORK_DIR/pyside6-packed")"

    mkdir -p "$WORK_DIR/pyside6-repaired"
    auditwheel repair "$packed_wheel" --wheel-dir "$WORK_DIR/pyside6-repaired" \
        --no-update-tags \
        --exclude 'libglib*.so.*' --exclude 'libgobject*.so.*' \
        --exclude 'libgio*.so.*' --exclude 'libX11*.so.*' \
        --exclude 'libGLX*.so.*' --exclude 'libGL*.so.*' \
        --exclude 'libGLdispatch*.so.*' --exclude 'libxcb*.so.*' \
        --exclude 'libXau*.so.*' --exclude 'libqwayland*.so.*' \
        --exclude 'libXdmcp*.so.*' --exclude 'libX*.so*' \
        --exclude 'libgdk*.so*' --exclude 'libgio*.so*' \
        --exclude 'libgmodule*.so*' --exclude 'libgtk*.so*' \
        --exclude 'libwayland*.so.*' --exclude 'libshiboken*.so.*' \
        --exclude 'libQt*.so*'
    repaired_wheel="$(find "$WORK_DIR/pyside6-repaired" -maxdepth 1 -type f -name '*.whl' -print -quit)"
    [[ -n "$repaired_wheel" ]] || die "auditwheel 未生成 pyside6 wheel"
    fix_embedded_rpaths "$repaired_wheel"
    cp -a "$repaired_wheel" "$OUTPUT_DIR/"
}

retag_shiboken6() {
    local unpacked_dir packed_wheel
    unpacked_dir="$(unpack_wheel "$SHIBOKEN_RAW" "$WORK_DIR/shiboken6-unpack")"
    set_wheel_tag "$unpacked_dir"
    packed_wheel="$(pack_wheel "$unpacked_dir" "$WORK_DIR/shiboken6-packed")"
    cp -a "$packed_wheel" "$OUTPUT_DIR/"
}

repair_generator() {
    local unpacked_dir packed_wheel repaired_wheel
    unpacked_dir="$(unpack_wheel "$GENERATOR_RAW" "$WORK_DIR/generator-unpack")"
    set_wheel_tag "$unpacked_dir"
    packed_wheel="$(pack_wheel "$unpacked_dir" "$WORK_DIR/generator-packed")"
    mkdir -p "$WORK_DIR/generator-repaired"
    auditwheel repair "$packed_wheel" --wheel-dir "$WORK_DIR/generator-repaired" \
        --no-update-tags
    repaired_wheel="$(find "$WORK_DIR/generator-repaired" -maxdepth 1 -type f -name '*.whl' -print -quit)"
    [[ -n "$repaired_wheel" ]] || die "auditwheel 未生成 shiboken6_generator wheel"
    fix_embedded_rpaths "$repaired_wheel"
    cp -a "$repaired_wheel" "$OUTPUT_DIR/"
}

repair_pyside6
retag_shiboken6
repair_generator

mapfile -t FINAL_WHEELS < <(find "$OUTPUT_DIR" -maxdepth 1 -type f \
    -name "*-${VERSION}-${TARGET_TAG}.whl" -printf '%p\n' | sort)
[[ ${#FINAL_WHEELS[@]} -eq 3 ]] || \
    die "期望在 $OUTPUT_DIR 中得到 3 个 wheel，实际为 ${#FINAL_WHEELS[@]}"

log "检查最终 wheel 的 ZIP 完整性和 tag"
for wheel_path in "${FINAL_WHEELS[@]}"; do
    "$PYTHON" - "$wheel_path" "$TARGET_TAG" <<'PY'
from pathlib import Path
import sys
import zipfile

wheel = Path(sys.argv[1])
expected_tag = sys.argv[2]
with zipfile.ZipFile(wheel) as archive:
    bad_file = archive.testzip()
    if bad_file:
        raise SystemExit(f"wheel ZIP 损坏: {wheel}: {bad_file}")
    wheel_metadata = next(name for name in archive.namelist() if name.endswith(".dist-info/WHEEL"))
    metadata = archive.read(wheel_metadata).decode("utf-8")
    if f"Tag: {expected_tag}\n" not in metadata:
        raise SystemExit(f"wheel tag 不正确: {wheel}")
print(f"✅ {wheel.name} ({wheel.stat().st_size / 1024 / 1024:.1f} MiB)")
PY
done

if [[ "$UPLOAD" -eq 1 ]]; then
    log "上传 3 个 wheel 到 twine 仓库 gitlab"
    twine upload -r gitlab "${FINAL_WHEELS[@]}"
fi

log "✅ 全部完成，产物目录: $OUTPUT_DIR"
