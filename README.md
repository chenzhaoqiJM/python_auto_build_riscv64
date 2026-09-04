# Python Wheel Automated Build Guide

This project automates building Python wheel packages on Bianbu Linux for the RISC-V (`riscv64`) architecture and uploading them to the Spacemit GitLab PyPI repository.

Spacemit GitLab PyPI repository: https://git.spacemit.com/groups/archive/-/packages/

## Directory Structure

```
python_auto_build/
├── sys_setup.sh              # System environment initialization script
├── env_common.sh             # Common environment variable configuration
├── common_func.sh            # Common function library
├── build_most_common/        # Build scripts for frequently used packages
├── build_pypi/               # Batch builds for community PyPI packages
├── build_version/            # Builds for package version updates
├── common_py/                # Common Python utilities and upload scripts
├── special_care/             # Build logic for packages requiring special handling
├── dynamic_env/              # Dynamic environment variable loading
├── manual_build/             # Manually triggered build scripts
├── test_scripts/             # Test scripts
├── others_scripts/           # Other helper scripts
└── bin/                      # Executable tools
```

## Environment Setup

### Supported System Versions

| glibc Version | System Version | Platform Tag |
|---------------|----------------|--------------|
| 2.39 | Bianbu Desktop v2.2 (Ubuntu 24.04) | manylinux_2_39_riscv64 |
| 2.41 | Bianbu Desktop v3.x | manylinux_2_41_riscv64 |
| 2.43 | Bianbu Desktop v4.x | manylinux_2_43_riscv64 |

**Base system**: Bianbu Desktop v2.2 https://nexus.bianbu.xyz/repository/image/k1/version/bianbu/v2.2/bianbu-24.04-desktop-k1-v2.2-20250430190125.zip

The upstream distribution is Ubuntu 24.04. GCC 14 is used for improved RVV (RISC-V Vector Extension) support.

Packages for Python 3.12 should preferably be built on Bianbu 2.x to avoid glibc compatibility issues.

### Initialization

Configure passwordless `sudo`:

```
echo "$USER ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/nopasswd_$USER
```

Run the system environment initialization script:

```bash
./sys_setup.sh
```

This script automatically:

- Installs build dependencies, including Python, compilation toolchains, and development libraries
- Configures GCC 14, installing and switching to it automatically if the current version does not meet the requirement
- Configures domestic mirrors for the pip and uv package managers
- Configures `.pypirc` for package uploads
- Downloads prebuilt third-party libraries, including Qt5, Arrow, FFmpeg, MuJoCo, and CycloneDDS
- Installs the Rust toolchain

### Supported Python Versions

Set the target Python version before building:

```bash
export BUILD_FOR_VERSION=3.12  # Supported: 3.9, 3.10, 3.11, 3.12, 3.13, 3.13t, 3.14, 3.14t
```

> **Note**: `3.13t` and `3.14t` are free-threaded (no-GIL) builds.

---

## Build Modules

### build_most_common - Frequently Used Packages

Builds the most frequently used Python packages, including core packages such as NumPy, SciPy, opencv-python, and pandas.

**Package list**: `hp_pkgs.txt`

**Build a single package**:

```bash
./build_one.sh numpy
```

**Build for multiple Python versions sequentially**:

```bash
BUILD_FOR_VERSION="3.9 3.10 3.11" ./build_one.sh numpy scipy
# Alternatively, use comma-separated versions
BUILD_FOR_VERSIONS="3.12,3.13,3.14" ./build_one.sh numpy scipy
```

Versions are built one by one in the specified order. Each version uses an independent virtual environment, cache, and failure log. If a version fails, the remaining versions are still built; after all builds finish, the command exits with a failure status if any build failed.

**Build from a source directory** (suitable after modifying the source code):

```bash
./build_from_src.sh /path/to/source/cmake-4.1.0
```

**Build all frequently used packages in a batch** (using uv):

```bash
./02hp_build_uv.sh
```

The batch builder resolves each requested package's runtime dependency closure
for the selected Python interpreter. Dependencies are processed before the
requested package and use their own `dynamic_env` and `special_care` handlers.
If official PyPI provides a wheel accepted by the target interpreter, the build
is skipped without requiring its manylinux tag to equal `AUDITWHEEL_PLAT_DEF`.

---

### build_pypi - Batch Builds for Community PyPI Packages

#### Official Top PyPI Package Builds

Builds active community packages one by one based on the [Top PyPI Packages](https://hugovk.github.io/top-pypi-packages/) ranking.

**Package list**: `top_pypi_package_names.txt`

```bash
./02official_pypi_build_uv.sh
```

#### Updates for Packages Already Available on Spacemit PyPI

Keeps packages already available on the Spacemit PyPI index up to date.

```bash
./02spacemit_pypi_build_uv.sh
```

---

### build_version - Package Version Builds

Builds all relevant releases in each supported Python version cycle for packages listed at https://git.spacemit.com/api/v4/projects/33/packages/pypi/simple.

**Update all package versions in a batch**:

```bash
./01version_build_uv.sh
```

**Skip list**: `skip_pkgs.txt` (records packages that should be skipped)

**Build recent versions of specified packages**:

```bash
./02single_build_uv.sh opencv-python opencv-contrib-python
```

---

### special_care - Special Package Builds

Defines build workflows for packages that require patches or other special handling.

**Entry point**: `special_builder.py`

**Packages currently receiving special handling**:

- `opencv-python`, `opencv-contrib-python`, `opencv-python-headless`, `opencv-contrib-python-headless`
- `numpy`, `matplotlib`, `onnx`
- `lintrunner`, `mmcif`, `glfw`
- `pyqt5`, `pyqt6`
- `curl-cffi`

**Package-specific build logic**: Each specially handled package is defined in a `build_xxx.py` file.

---

### dynamic_env - Dynamic Environment Loading

Dynamically loads the environment variables required by each package.

**Entry-point script**: `env_loader.sh`

**Supported environment modules**:

- `arrow_env.sh` - Apache Arrow
- `av_env.sh` - PyAV (FFmpeg)
- `opencv_env.sh` - OpenCV
- `qt5_env.sh` / `qt6_env.sh` - Qt-related settings
- `mujoco_env.sh` - MuJoCo
- `cyclonedds_env.sh` - CycloneDDS
- `llvmlite_env.sh` - llvmlite
- `faiss_env.sh` - Faiss
- `pymupdf_env.sh` - PyMuPDF
- `pemja_env.sh` - PemJa
- `pynacl.sh` - PyNaCl

**Usage**:

```bash
source dynamic_env/env_loader.sh <package_name>
load_env      # Load the environment
# ... build operations ...
unload_env    # Unload the environment
```

---

### common_py - Common Python Utilities

Contains wheel repair, packaging, and upload scripts.

| File | Function |
|------|----------|
| `00upload_with_repair.py` | Post-processes and uploads wheel packages |
| `01upload_with_repair_src.py` | Uploads packages after building from source |
| `check_whl.py` | Validates wheel packages |
| `download_whl_sdist.py` | Downloads wheels or source distributions |
| `upload_from_dir.py` | Uploads packages from a directory in a batch |

**`fix_whl` subdirectory**:

| File | Function |
|------|----------|
| `fix_whl_rpath.py` | Repairs the rpath of shared libraries under the `.libs` directory |
| `fix_whl_name.py` | Repairs wheel package names |
| `fix_rpath_common.py` | Common rpath repair functions |
| `fix_z_qt5.py` / `fix_z_qt6.py` | Qt5/Qt6-specific repairs |

---

### manual_build - Manual Builds

Manually triggered build scripts that require additional setup.

| Script | Function |
|--------|----------|
| `01stag-python.sh` | Builds Stag Python (migrated to `special_care/build_stag_python.py`; it can be triggered with `build_most_common/build_one.sh stag-python`) |
| `02onnxruntime.sh` | Builds ONNX Runtime |
| `04pytorch.sh` | Builds PyTorch |
| `04torchvision.sh` | Builds TorchVision |
| `04torchaudio.sh` | Builds TorchAudio |
| `04torch_upload.py` | Uploads the PyTorch package family |

---

## Key Environment Variables

| Variable | Description |
|----------|-------------|
| `BUILD_FOR_VERSION` | Target Python version (3.9/3.10/3.11/3.12/3.13/3.13t/3.14/3.14t) |
| `AUDITWHEEL_PLAT_DEF` | auditwheel platform tag (detected automatically) |
| `FROM_SOURCE_FLAG` | Whether to force a source build (0/1) |
| `UV_INDEX_URL` | Primary uv package index |
| `UV_EXTRA_INDEX_URL` | Additional uv package index (Spacemit PyPI) |

---

## PyPI Upload Configuration

Upload destination: https://git.spacemit.com/api/v4/projects/33/packages/pypi

The `~/.pypirc` configuration file is generated automatically by `sys_setup.sh` using the contents of `pypirc.txt`.

---

## Prebuilt Third-Party Libraries

The following libraries are downloaded automatically to `/opt/ext/` when `sys_setup.sh` runs:

- **Qt5**: `/opt/Qt5.15.16`
- **Apache Arrow**: `/opt/ext/arrow/`
- **FFmpeg**: `/opt/ext/ffmpeg/`
- **MuJoCo**: `/opt/ext/mujoco/`
- **CycloneDDS**: `/opt/ext/cyclonedds/`

Download source: `https://archive.spacemit.com/ros2/prebuilt_libs/`
