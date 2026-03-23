

# for pyside6
auditwheel repair PySide6-6.9.2-cp37-abi3-linux_riscv64.whl --no-update-tags \
  --exclude 'libglib*.so.*' \
  --exclude 'libgobject*.so.*' \
  --exclude 'libgio*.so.*' \
  --exclude 'libX11*.so.*' \
  --exclude 'libGLX*.so.*' \
  --exclude 'libGL*.so.*' \
  --exclude 'libGLdispatch*.so.*' \
  --exclude 'libxcb*.so.*' \
  --exclude 'libXau*.so.*' \
  --exclude 'libqwayland*.so.*' \
  --exclude 'libXdmcp*.so.*' \
  --exclude 'libX*.so*' \
  --exclude 'libgdk*.so*' \
  --exclude 'libgio*.so*' \
  --exclude 'libgmodule*.so*' \
  --exclude 'libgtk*.so*' \
  --exclude 'libwayland*.so.*' \
  --exclude 'libshiboken*.so.*'
  
