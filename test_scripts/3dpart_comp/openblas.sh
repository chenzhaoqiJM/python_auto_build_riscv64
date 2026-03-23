
mkdir -p build && cd build

cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$HOME/ext/openblas-install \
  -DCMAKE_C_FLAGS="-O3 -march=rv64gcv -march=rv64gcv" \
  -DCMAKE_CXX_FLAGS="-O3 -march=rv64gcv -march=rv64gcv" \
  -DCMAKE_ASM_FLAGS="-march=rv64gcv" \
  -DBUILD_SHARED_LIBS=ON \
  -DBUILD_WITHOUT_CBLAS=ON

make -j$(nproc)
make install
