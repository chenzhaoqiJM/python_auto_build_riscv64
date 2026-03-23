# Python whl 自动化构建说明

本项目用于在 RISC-V 架构 (riscv64) 的 Bianbu Linux 系统上自动化构建 Python wheel 包，并上传至 Spacemit GitLab PyPI 仓库。

## 目录结构

```
python_auto_build/
├── sys_setup.sh              # 系统环境初始化脚本
├── env_common.sh             # 通用环境变量配置
├── common_func.sh            # 通用函数库
├── build_most_common/        # 高频包构建脚本
├── build_pypi/               # PyPI 社区包批量构建
├── build_version/            # 版本更新构建
├── common_py/                # Python 通用工具和上传脚本
├── special_care/             # 需要特殊处理的包构建逻辑
├── dynamic_env/              # 动态环境变量加载
├── manual_build/             # 手动触发的构建脚本
├── test_scripts/             # 测试脚本
├── others_scripts/           # 其他辅助脚本
└── bin/                      # 可执行工具
```

## 环境设置

### 支持的系统版本

| glibc 版本 | 系统版本 | 平台标签 |
|-----------|---------|---------|
| 2.39 | Bianbu Desktop v2.2 (Ubuntu 24.04) | manylinux_2_39_riscv64 |
| 2.41 | Bianbu Desktop v3.x | manylinux_2_41_riscv64 |
| 2.42 | Bianbu Desktop v2.6-pre | manylinux_2_42_riscv64 |

**基础系统**: Bianbu Desktop v2.2 https://nexus.bianbu.xyz/repository/image/k1/version/bianbu/v2.2/bianbu-24.04-desktop-k1-v2.2-20250430190125.zip

上游为 Ubuntu 24.04，使用 GCC 14 以更好地支持 RVV (RISC-V Vector Extension)。

python3.12的包建议先在bianbu 2.x上构建，以避免glibc兼容性问题。

### 初始化

执行系统环境初始化脚本：

```bash
./sys_setup.sh
```

此脚本将自动完成：
- 安装构建依赖 (包括 Python、编译工具链、各类开发库等)
- 配置 GCC 14 (如版本不满足会自动安装并切换)
- 配置 pip 和 uv 包管理器的国内镜像源
- 设置 `.pypirc` 用于包上传
- 下载预编译的第三方库 (Qt5、Arrow、FFmpeg、MuJoCo、CycloneDDS 等)
- 安装 Rust 工具链

### 支持的 Python 版本

构建前需要设置目标 Python 版本：

```bash
export BUILD_FOR_VERSION=3.12  # 支持: 3.9, 3.10, 3.11, 3.12, 3.13, 3.13t, 3.14, 3.14t
```

> **注意**: `3.13t` 和 `3.14t` 为 free-threading (无 GIL) 版本。

---

## 构建模块

### build_most_common - 高频包构建

用于构建使用频率最高的 Python 包，包含 numpy、scipy、opencv-python、pandas 等核心包。

**包列表**: `hp_pkgs.txt`

**构建单个包**:
```bash
./build_one.sh numpy
```

**从源码目录构建** (适合修改源码后的构建):
```bash
./build_from_src.sh /path/to/source/cmake-4.1.0
```

**批量构建所有高频包** (使用 uv):
```bash
./02hp_build_uv.sh
```

---

### build_pypi - PyPI 社区包批量构建

#### 官方 PyPI Top 包构建

基于 [Top PyPI Packages](https://hugovk.github.io/top-pypi-packages/) 排行榜，逐个构建社区活跃包。

**包列表**: `top_pypi_package_names.txt`

```bash
./02official_pypi_build_uv.sh
```

#### Spacemit PyPI 源已有包更新

保持 Spacemit PyPI 源中已有包的版本最新。

```bash
./02spacemit_pypi_build_uv.sh
```

---

### build_version - 版本更新构建

用于完善 https://git.spacemit.com/api/v4/projects/33/packages/pypi/simple 里 Python 包的相应python版本周期下的所有版本。

**批量更新所有包版本**:
```bash
./01version_build_uv.sh
```

**跳过包列表**: `skip_pkgs.txt` (记录需要跳过的包)

**构建指定包的近期版本**:
```bash
./02single_build_uv.sh opencv-python opencv-contrib-python
```

---

### special_care - 特殊包构建

定义了需要打 patch 或特殊处理的包构建流程。

**入口**: `special_builder.py`

**当前支持的特殊处理包**:
- `opencv-python`, `opencv-contrib-python`, `opencv-python-headless`, `opencv-contrib-python-headless`
- `numpy`, `matplotlib`, `onnx`
- `lintrunner`, `mmcif`, `glfw`
- `pyqt5`, `pyqt6`
- `curl-cffi`

**单独构建逻辑**: 每个特殊包在 `build_xxx.py` 文件中定义。

---

### dynamic_env - 动态环境加载

根据不同包名动态加载所需的环境变量。

**入口脚本**: `env_loader.sh`

**支持的环境模块**:
- `arrow_env.sh` - Apache Arrow
- `av_env.sh` - PyAV (FFmpeg)
- `opencv_env.sh` - OpenCV
- `qt5_env.sh` / `qt6_env.sh` - Qt 相关
- `mujoco_env.sh` - MuJoCo
- `cyclonedds_env.sh` - CycloneDDS
- `llvmlite_env.sh` - llvmlite
- `faiss_env.sh` - Faiss
- `pymupdf_env.sh` - PyMuPDF
- `pemja_env.sh` - PemJa
- `pynacl.sh` - PyNaCl

**使用方式**:
```bash
source dynamic_env/env_loader.sh <package_name>
load_env      # 加载环境
# ... 构建操作 ...
unload_env    # 卸载环境
```

---

### common_py - 通用 Python 工具

记录了修复脚本和打包上传脚本。

| 文件 | 功能 |
|-----|-----|
| `00upload_with_repair.py` | whl 包后处理和上传 |
| `01upload_with_repair_src.py` | 从源码构建后上传 |
| `check_whl.py` | 检查 whl 包有效性 |
| `download_whl_sdist.py` | 下载 whl 或 sdist |
| `upload_from_dir.py` | 从目录批量上传 |

**fix_whl 子目录**:
| 文件 | 功能 |
|-----|-----|
| `fix_whl_rpath.py` | 修复 `.libs` 文件夹下动态库的 rpath |
| `fix_whl_name.py` | 修复 whl 包名 |
| `fix_rpath_common.py` | 通用 rpath 修复函数 |
| `fix_z_qt5.py` / `fix_z_qt6.py` | Qt5/Qt6 特殊修复 |

---

### manual_build - 手动构建

手动触发的构建脚本，需要进行一些额外设置。

| 脚本 | 功能 |
|-----|-----|
| `01stag-python.sh` | Stag Python 构建（已迁移到 `special_care/build_stag_python.py`，可由 `build_most_common/build_one.sh stag-python` 触发） |
| `02onnxruntime.sh` | ONNX Runtime 构建 |
| `04pytorch.sh` | PyTorch 构建 |
| `04torchvision.sh` | TorchVision 构建 |
| `04torchaudio.sh` | TorchAudio 构建 |
| `04torch_upload.py` | PyTorch 系列上传 |

---


## 关键环境变量

| 变量 | 说明 |
|-----|-----|
| `BUILD_FOR_VERSION` | 目标 Python 版本 (3.9/3.10/3.11/3.12/3.13/3.13t/3.14/3.14t) |
| `AUDITWHEEL_PLAT_DEF` | auditwheel 平台标签 (自动检测) |
| `FROM_SOURCE_FLAG` | 是否强制从源码构建 (0/1) |
| `UV_INDEX_URL` | uv 主索引源 |
| `UV_EXTRA_INDEX_URL` | uv 额外索引源 (Spacemit PyPI) |

---

## PyPI 上传配置

上传目标: https://git.spacemit.com/api/v4/projects/33/packages/pypi

配置文件 `~/.pypirc` 由 `sys_setup.sh` 自动生成，内容来自 `pypirc.txt`。

---

## 第三方预编译库

以下库将在 `sys_setup.sh` 执行时自动下载到 `/opt/ext/`:

- **Qt5**: `/opt/Qt5.15.16`
- **Apache Arrow**: `/opt/ext/arrow/`
- **FFmpeg**: `/opt/ext/ffmpeg/`
- **MuJoCo**: `/opt/ext/mujoco/`
- **CycloneDDS**: `/opt/ext/cyclonedds/`

下载源: `https://archive.spacemit.com/ros2/prebuilt_libs/`
