#!/bin/bash
# run.sh - 启动构建监控服务
# 在 x64 服务器 (10.0.90.124) 上运行

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python 和 Flask
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi

# 安装依赖
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installing Flask..."
    pip3 install flask --user
fi

# 创建必要目录
mkdir -p logs static

echo "============================================"
echo "🚀 Build Monitor Server"
echo "============================================"
echo "📊 Dashboard: http://10.0.90.124:5000"
echo "📡 API Base:  http://10.0.90.124:5000/api"
echo "============================================"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# 启动服务
python3 app.py
