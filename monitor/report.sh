#!/bin/bash
# report.sh - 构建状态上报函数库
# 用法: source monitor/report.sh

# 监控服务器地址（根据实际情况修改）
MONITOR_SERVER="${MONITOR_SERVER:-http://10.0.90.124:5050}"

# 获取机器标识
get_machine_id() {
    # 优先使用 MACHINE_ID 环境变量，否则使用 hostname
    echo "${MACHINE_ID:-$(hostname)}"
}

# 上报构建开始
# 用法: report_start <package_name> [script_name]
# 返回: build_id (存储在 BUILD_ID 环境变量中)
report_start() {
    local package="$1"
    local script="${2:-}"
    local machine=$(get_machine_id)
    local python_version="${BUILD_FOR_VERSION:-unknown}"
    
    local response=$(curl -s -X POST "${MONITOR_SERVER}/api/build/start" \
        -H "Content-Type: application/json" \
        -d "{\"machine\": \"${machine}\", \"package\": \"${package}\", \"script\": \"${script}\", \"python_version\": \"${python_version}\"}" \
        2>/dev/null)
    
    # 提取 build_id
    local build_id=$(echo "$response" | grep -oP '"id"\s*:\s*\K\d+' 2>/dev/null || echo "")
    
    if [ -n "$build_id" ]; then
        export CURRENT_BUILD_ID="$build_id"
        echo "[Monitor] 📤 Started build #${build_id}: ${package}"
    else
        echo "[Monitor] ⚠️  Failed to report start for ${package}"
        export CURRENT_BUILD_ID=""
    fi
}

# 上报构建完成
# 用法: report_finish <status> [log_file]
# status: success / failed
report_finish() {
    local status="${1:-success}"
    local log_file="${2:-}"
    local build_id="${CURRENT_BUILD_ID:-}"
    
    if [ -z "$build_id" ]; then
        echo "[Monitor] ⚠️  No build_id, skipping finish report"
        return 1
    fi
    
    # 上报状态
    curl -s -X POST "${MONITOR_SERVER}/api/build/finish" \
        -H "Content-Type: application/json" \
        -d "{\"id\": ${build_id}, \"status\": \"${status}\"}" \
        >/dev/null 2>&1
    
    # 如果有日志文件且失败，上传日志
    if [ -n "$log_file" ] && [ -f "$log_file" ]; then
        curl -s -X POST "${MONITOR_SERVER}/api/build/log" \
            -F "id=${build_id}" \
            -F "log=@${log_file}" \
            >/dev/null 2>&1
        echo "[Monitor] 📝 Uploaded log for build #${build_id}"
    fi
    
    echo "[Monitor] 📥 Finished build #${build_id}: ${status}"
    unset CURRENT_BUILD_ID
}

# 快捷函数：执行命令并自动上报
# 用法: run_with_report <package_name> <command...>
run_with_report() {
    local package="$1"
    shift
    local cmd="$@"
    local log_file=$(mktemp /tmp/build_${package}_XXXXXX.log)
    
    report_start "$package"
    
    # 执行命令并捕获输出
    if eval "$cmd" 2>&1 | tee "$log_file"; then
        report_finish "success"
        rm -f "$log_file"
    else
        report_finish "failed" "$log_file"
        # 保留失败日志一段时间
    fi
}
