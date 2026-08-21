# Open3D v0.19.0 Python 3.14 RISC-V Wheel 编译总结

## 1. 目标与最终产物

在远程主机的 Open3D 源码目录中，为 Python 3.14 编译 Open3D v0.19.0 的 RISC-V 64 位 wheel。

最终 wheel：

```text
/home/bianbu26/Open3D/build_py314/lib/python_package/pip_package/open3d-0.19.0+1e7b17438-cp314-cp314-manylinux_2_43_riscv64.whl
```

产物信息：

- Open3D：`0.19.0+1e7b17438`
- Python/ABI 标签：`cp314-cp314`
- 平台标签：`manylinux_2_43_riscv64`
- 文件大小：`12,893,679 bytes`，约 `12.3 MiB`

## 2. 构建环境

| 项目 | 值 |
|---|---|
| 源码目录 | `/home/bianbu26/Open3D` |
| 源码提交 | `1e7b17438687a0b0c1e5a7187321ac7044afe275` |
| 源码标签 | `v0.19.0` |
| 架构 | `riscv64` |
| Python | `3.14.4` |
| CMake | `4.2.3` |
| C++ 编译器 | GCC/G++ `15.2.0` |
| Generator | Ninja |
| 构建类型 | Release |
| 构建目录 | `/home/bianbu26/Open3D/build_py314` |
| 构建日志 | `/home/bianbu26/Open3D/build_py314/build-pip-package.log` |

## 3. 最终构建选项

核心配置：

```text
BUILD_PYTHON_MODULE=ON
BUILD_CUDA_MODULE=OFF
BUILD_ISPC_MODULE=OFF
BUILD_GUI=OFF
BUILD_WEBRTC=OFF
BUILD_JUPYTER_EXTENSION=OFF
BUILD_EXAMPLES=OFF
BUILD_UNIT_TESTS=OFF
BUILD_BENCHMARKS=OFF
BUILD_SHARED_LIBS=OFF
GLIBCXX_USE_CXX11_ABI=ON
USE_BLAS=ON
USE_SYSTEM_BLAS=ON
USE_SYSTEM_CURL=ON
USE_SYSTEM_OPENSSL=ON
USE_SYSTEM_TBB=ON
USE_SYSTEM_VTK=ON
```

使用系统依赖的主要原因是 Open3D v0.19.0 的部分预编译第三方库只适用于 x86_64；在 RISC-V 上会在最终链接阶段出现 `EM: 62` 或 `file in wrong format`。

## 4. 安装必要的系统依赖

主机已有大部分开发依赖。本次补充安装了 LAPACKE、curl 和 OpenSSL 开发包：

```bash
sudo apt-get update
sudo apt-get install -y \
    liblapacke-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    pkg-config
```

最终还使用了系统安装的：

- BLAS/LAPACK/LAPACKE
- curl
- OpenSSL
- VTK 9.5.2
- TBB 2022.3.0

## 5. 源码兼容性修改

Open3D v0.19.0 原生未完整支持 RISC-V、CMake 4.2 和 GCC 15，因此进行了以下本地修改。

### 5.1 增加 RISC-V 架构识别

文件：`CMakeLists.txt`

在 Linux 架构检测中增加：

```cmake
elseif(PROCESSOR_ARCH MATCHES "^riscv")
    set(LINUX_RISCV64 TRUE)
```

该变量用于控制 RISC-V 不支持的第三方组件和架构专用参数。

### 5.2 兼容 CMake 4 的旧 ExternalProject

文件：`3rdparty/find_dependencies.cmake`

向所有第三方 `ExternalProject` 的 CMake 参数加入：

```cmake
-DCMAKE_POLICY_VERSION_MINIMUM=3.5
```

解决旧版 zlib 等依赖在 CMake 4.2.3 下的错误：

```text
Compatibility with CMake < 3.5 has been removed from CMake.
```

只在 Open3D 顶层传入该参数不一定会传播到独立的 `ExternalProject_Add` 配置过程，因此需要加入共享的 ExternalProject 参数列表。

### 5.3 UVAtlas 禁用 SIMD intrinsic

文件：`3rdparty/uvatlas/uvatlas.cmake`

向 UVAtlas 自身的构建参数加入：

```cmake
-DCMAKE_CXX_FLAGS=-D_XM_NO_INTRINSICS_
```

该参数必须传入 UVAtlas 的独立 CMake 构建，而不能只加到 Open3D 主目标，否则 UVAtlas 本身仍会尝试编译 x86/ARM intrinsic。

Open3D 主体也使用：

```text
-D_XM_NO_INTRINSICS_
```

### 5.4 禁用 RISC-V 上不受支持的 Embree

文件：

- `3rdparty/find_dependencies.cmake`
- `3rdparty/embree/embree.cmake`
- `cpp/open3d/t/geometry/RaycastingScene.cpp`

Embree 没有可用于当前 RISC-V 平台的 ISA 后端。将 Embree 依赖在 `LINUX_RISCV64` 下禁用，并为 `RaycastingScene` 提供可链接的降级实现，以保留 Python 模块整体的导入能力。

限制：该 wheel 的 Embree 光线投射相关功能不可正常使用；调用相应 API 时只会得到降级结果。点云、张量、常规几何和 I/O 等已验证功能不受此项影响。

### 5.5 避免向 RISC-V 编译器传递 `-m64`

文件：`3rdparty/find_dependencies.cmake`

原逻辑在所有 Unix 平台上向 MKL/BLAS 接口传播 `-m64`，但 RISC-V GCC 不支持该 x86 专用参数。修改为：

```cmake
if(NOT LINUX_RISCV64)
    target_compile_options(3rdparty_blas INTERFACE
        "$<$<COMPILE_LANGUAGE:CXX>:-m64>")
endif()
```

最终配置改用系统 BLAS，避免使用 Open3D 下载的 x86_64 MKL。

### 5.6 GCC 15 严格头文件依赖

文件：`cpp/open3d/core/SmallVector.h`

补充直接依赖：

```cpp
#include <cstdint>
```

解决 `uint32_t`、`uint64_t` 未声明以及随后产生的 `SizeVector` 级联编译错误。

## 6. 第三方错误架构库排查

### 6.1 curl

首次链接 Python 扩展时出现：

```text
Relocations in generic ELF (EM: 62)
libcurl.a: error adding symbols: file in wrong format
```

`EM: 62` 表示 x86_64。Open3D 的判断条件为“Linux 且不是 aarch64”时下载预编译 curl，因此 RISC-V 被错误归入 x86_64 路径。

处理方式：

```text
USE_SYSTEM_CURL=ON
USE_SYSTEM_OPENSSL=ON
```

curl 与 OpenSSL 应配套切换为系统库，避免静态 curl 与不匹配的 BoringSSL/OpenSSL 混用。

### 6.2 MKL

Open3D 下载的是：

```text
mkl_static-2024.1.0-linux_x86_64.tar.xz
```

该包不适用于 RISC-V，同时还会传播 `-m64`。处理方式：

```text
USE_BLAS=ON
USE_SYSTEM_BLAS=ON
```

并安装完整的 BLAS/LAPACK/LAPACKE 开发接口。

### 6.3 VTK

第二次最终链接出现：

```text
libvtkFiltersGeneral-9.1.a: Relocations in generic ELF (EM: 62)
file in wrong format
```

说明 Open3D 选择了预编译 x86_64 VTK。主机已有原生 RISC-V VTK 9.5.2，因此切换为：

```text
USE_SYSTEM_VTK=ON
USE_SYSTEM_TBB=ON
```

系统 VTK 会带入系统 TBB。若只打开系统 VTK、不同时使用系统 TBB，Open3D 的旧 TBB 构建逻辑可能出现：

```text
install TARGETS given target "tbb" which does not exist
```

所以这两个选项需要成组切换。

## 7. 最终配置命令

在源码目录执行：

```bash
cd /home/bianbu26/Open3D

cmake -S . -B build_py314 -GNinja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_FLAGS="-D_XM_NO_INTRINSICS_ -DOPEN3D_RISCV64" \
    -DCMAKE_INSTALL_PREFIX=/home/bianbu26/Open3D/build_py314/install \
    -DPython3_EXECUTABLE=/usr/bin/python3.14 \
    -DBUILD_PYTHON_MODULE=ON \
    -DBUILD_CUDA_MODULE=OFF \
    -DBUILD_ISPC_MODULE=OFF \
    -DBUILD_GUI=OFF \
    -DBUILD_WEBRTC=OFF \
    -DBUILD_JUPYTER_EXTENSION=OFF \
    -DBUILD_EXAMPLES=OFF \
    -DBUILD_UNIT_TESTS=OFF \
    -DBUILD_BENCHMARKS=OFF \
    -DBUILD_SHARED_LIBS=OFF \
    -DGLIBCXX_USE_CXX11_ABI=ON \
    -DUSE_BLAS=ON \
    -DUSE_SYSTEM_BLAS=ON \
    -DUSE_SYSTEM_CURL=ON \
    -DUSE_SYSTEM_OPENSSL=ON \
    -DUSE_SYSTEM_VTK=ON \
    -DUSE_SYSTEM_TBB=ON
```

## 8. 编译 wheel

```bash
cd /home/bianbu26/Open3D
cmake --build build_py314 --target pip-package -j8 \
    2>&1 | tee -a build_py314/build-pip-package.log
```

成功标志：

```text
pip wheel created at /home/bianbu26/Open3D/build_py314/lib/python_package/pip_package
```

注意：RISC-V 上完整 Release 编译耗时较长。控制端超时不代表构建失败，应检查远程 Ninja/编译器进程、日志和最终退出码，不能根据中间的 `219/400` 等进度认定成功。

## 9. Wheel 标签检查

查找 wheel：

```bash
find build_py314/lib/python_package/pip_package \
    -maxdepth 1 -name '*.whl' -print
```

解析文件名标签：

```bash
python3.14 - <<'PY'
from packaging.utils import parse_wheel_filename

name = "open3d-0.19.0+1e7b17438-cp314-cp314-manylinux_2_43_riscv64.whl"
print(parse_wheel_filename(name))
PY
```

同时检查 wheel 内部的 `*.dist-info/WHEEL`，确认：

```text
Wheel-Version: 1.0
Root-Is-Purelib: false
Tag: cp314-cp314-manylinux_2_43_riscv64
```

## 10. Python 3.14 安装与运行验证

创建隔离环境：

```bash
python3.14 -m venv /home/bianbu26/Open3D/build_py314/venv_verify314

VENV=/home/bianbu26/Open3D/build_py314/venv_verify314
WHEEL=/home/bianbu26/Open3D/build_py314/lib/python_package/pip_package/open3d-0.19.0+1e7b17438-cp314-cp314-manylinux_2_43_riscv64.whl

"$VENV/bin/pip" install "$WHEEL"
```

执行验证：

```bash
"$VENV/bin/python" - <<'PY'
import open3d as o3d

print("version:", o3d.__version__)
print("module:", o3d.__file__)

pcd = o3d.geometry.PointCloud()
print("point cloud empty:", pcd.is_empty())

tensor = o3d.core.Tensor([1, 2, 3])
print("tensor:", tensor.numpy().tolist())
print("build config:", o3d._build_config)
PY
```

实际验证结果：

```text
OPEN3D_VERSION= 0.19.0+1e7b17438
POINT_CLOUD_EMPTY= True
TENSOR= [1, 2, 3]
```

说明：使用 `pip install --no-deps` 只安装 wheel 后，首次导入会因缺少 `numpy`、`plotly` 等 Python 运行时依赖失败；这不是本地 `.so` 编译或 ABI 错误。安装 wheel 声明的依赖后，完整导入和 C++ 后端对象测试均成功。

## 11. 复现时的建议顺序

1. 确认源码为 v0.19.0，并记录 commit。
2. 使用独立目录 `build_py314`，不要与其他 Python ABI 共用。
3. 先应用 RISC-V、CMake 4、GCC 15 兼容修改。
4. 安装并启用系统 BLAS、curl、OpenSSL、VTK 和 TBB。
5. 配置时关闭 CUDA、ISPC、GUI、WebRTC 和不需要的测试/示例。
6. 构建 `pip-package`，保留追加式日志。
7. 如出现 `EM: 62`，检查链接命令中的静态库；这通常意味着 x86_64 预编译库被错误用于 RISC-V。
8. 构建退出码为 0 后，再检查 wheel 文件名和内部 WHEEL 标签。
9. 用准确的 Python 3.14 解释器创建隔离环境并安装完整依赖。
10. 验证版本、点云对象和 Tensor/NumPy 转换。

## 12. 已知功能限制

- 不包含 CUDA。
- 不包含 SYCL。
- 不包含 GUI 和 WebRTC。
- 不包含 Jupyter 扩展。
- 不包含 TensorFlow/PyTorch 自定义算子。
- Embree 在当前 RISC-V 架构不可用，因此 `RaycastingScene` 相关光线投射能力为降级实现，不应视为完整支持。
- wheel 标签为 `manylinux_2_43_riscv64`，只能用于满足相应 glibc 和 RISC-V ABI 条件的 Python 3.14 环境。
