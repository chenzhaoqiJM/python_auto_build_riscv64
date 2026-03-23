# 构建监控系统

轻量级分布式 Python 包构建状态监控系统。

## 快速开始

### 1. 启动监控服务（x64 服务器）

在 10.0.90.124 服务器上：

```bash
cd /path/to/python_auto_build/monitor
pip install -r requirements.txt
chmod +x run.sh
./run.sh
```

打开浏览器访问：**http://10.0.90.124:5050**

### 2. 使用带监控的构建脚本（RISC-V 构建机器）

```bash
# 设置环境变量
export BUILD_FOR_VERSION=3.12
export MACHINE_ID="riscv-build-01"  # 可选，默认使用 hostname

# 使用带监控的脚本（原脚本不变）
./build_most_common/02hp_build_uv_monitored.sh
./build_pypi/02official_pypi_build_uv_monitored.sh
./build_pypi/02spacemit_pypi_build_uv_monitored.sh
./build_version/01version_build_uv_monitored.sh
```

---

## 文件说明

| 文件 | 说明 |
|-----|-----|
| `monitor/app.py` | Flask 后端服务 |
| `monitor/static/index.html` | 监控仪表盘页面 |
| `monitor/report.sh` | 上报函数库 |
| `monitor/run.sh` | 服务启动脚本 |
| `*_monitored.sh` | 带监控的构建脚本副本 |

---

## API 说明

| 端点 | 方法 | 说明 |
|-----|-----|-----|
| `/api/build/start` | POST | 上报构建开始 |
| `/api/build/finish` | POST | 上报构建完成 |
| `/api/build/log` | POST | 上传失败日志 |
| `/api/builds` | GET | 获取构建列表 |
| `/api/build/<id>/log` | GET | 获取日志内容 |
| `/api/stats` | GET | 获取统计数据 |
| `/api/machines` | GET | 获取机器列表 |

---

## 自定义配置

环境变量：

```bash
export MONITOR_SERVER="http://10.0.90.124:5050"  # 监控服务器地址
export MACHINE_ID="my-build-machine"            # 机器标识
```
