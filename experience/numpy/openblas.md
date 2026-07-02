
要让 numpy 构建时用到 openblas-spacemit，关键是让 NumPy 的构建系统优先从 openblas-spacemit 找 BLAS/LAPACK，而不是系统默认 BLAS。

核心设置如下：

```
export PKG_CONFIG_PATH=/opt/openblas-spacemit/lib/pkgconfig
export LD_LIBRARY_PATH=/opt/openblas-spacemit/lib:${LD_LIBRARY_PATH:-}
export CFLAGS="-I/opt/openblas-spacemit/include ${CFLAGS:-}"
export LDFLAGS="-L/opt/openblas-spacemit/lib -Wl,-rpath,/opt/openblas-spacemit/lib ${LDFLAGS:-}"
export NPY_BLAS_ORDER=openblas
export NPY_LAPACK_ORDER=openblas
```

然后再执行构建，例如：

```
export SAVE_FINAL_WHL_TO_HOME=1
export BUILD_FOR_VERSION=3.12
~/python_auto_build_riscv64/build_most_common/build_from_src.sh /path/to/numpy-source
```