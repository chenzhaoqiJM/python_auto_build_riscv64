#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_PREFIX="pypi-build"
SERVICE_USER="${SERVICE_USER:-bianbu}"
INSTALL_DIR="${INSTALL_DIR:-/home/${SERVICE_USER}/python_auto_build_riscv64}"

PYTHON_VERSIONS=("3.9" "3.10" "3.11" "3.12" "3.13" "3.13t" "3.14" "3.14t")
SCRIPT_PATHS=(
  "build_most_common/02hp_build_uv.sh"
  "build_pypi/02official_pypi_build_uv.sh"
  "build_pypi/02spacemit_pypi_build_uv.sh"
  "build_version/01version_build_uv.sh"
)

prompt_select() {
  local title="$1"
  local result_var="$2"
  shift 2
  local items=("$@")
  local choice

  echo
  echo "${title}"
  for index in "${!items[@]}"; do
    printf '  %d) %s\n' "$((index + 1))" "${items[$index]}"
  done

  while true; do
    read -r -p "请输入序号 [1-${#items[@]}]: " choice
    if [[ "${choice}" =~ ^[0-9]+$ ]] && ((choice >= 1 && choice <= ${#items[@]})); then
      printf -v "${result_var}" '%s' "${items[$((choice - 1))]}"
      return 0
    fi
    echo "输入无效，请重新选择。"
  done
}

confirm() {
  local prompt="$1"
  local answer

  while true; do
    read -r -p "${prompt} [y/N]: " answer
    case "${answer}" in
      [Yy]|[Yy][Ee][Ss]) return 0 ;;
      ""|[Nn]|[Nn][Oo]) return 1 ;;
      *) echo "请输入 y 或 n。" ;;
    esac
  done
}

require_script_exists() {
  local script_path="$1"

  if [[ ! -f "${PROJECT_DIR}/${script_path}" ]]; then
    echo "错误：未找到脚本 ${PROJECT_DIR}/${script_path}" >&2
    exit 1
  fi
}

get_service_suffix() {
  local script_path="$1"

  case "${script_path}" in
    "build_most_common/02hp_build_uv.sh") echo "hp" ;;
    "build_pypi/02official_pypi_build_uv.sh") echo "of" ;;
    "build_pypi/02spacemit_pypi_build_uv.sh") echo "sp" ;;
    "build_version/01version_build_uv.sh") echo "ve" ;;
    *)
      echo "错误：未知脚本 ${script_path}" >&2
      exit 1
      ;;
  esac
}

main() {
  local python_version
  local selected_script
  local service_suffix
  local service_name
  local service_file
  local script_dir
  local script_name
  local work_dir
  local exec_start

  prompt_select "请选择 Python 版本：" python_version "${PYTHON_VERSIONS[@]}"
  prompt_select "请选择构建脚本：" selected_script "${SCRIPT_PATHS[@]}"
  require_script_exists "${selected_script}"

  service_suffix="$(get_service_suffix "${selected_script}")"
  service_name="${SERVICE_PREFIX}-${service_suffix}.service"
  service_file="/etc/systemd/system/${service_name}"
  script_dir="$(dirname "${selected_script}")"
  script_name="$(basename "${selected_script}")"
  work_dir="${INSTALL_DIR}/${script_dir}"
  exec_start="/bin/bash -lic 'BUILD_FOR_VERSION=${python_version} ${INSTALL_DIR}/${selected_script}'"

  cat <<EOF

将写入 systemd 服务：
--------------------------------------------------
[Unit]
Description=Python Auto Build Worker FOR ${service_suffix}
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${work_dir}
ExecStart=${exec_start}
Restart=on-failure
RestartSec=30
KillMode=control-group
TimeoutStopSec=300

[Install]
WantedBy=multi-user.target
--------------------------------------------------

服务文件：${service_file}
服务名称：${service_name}
本地仓库：${PROJECT_DIR}
安装目录：${INSTALL_DIR}
选择版本：${python_version}
选择脚本：${script_name}
EOF

  if ! confirm "确认写入并启动服务吗？"; then
    echo "已取消。"
    exit 0
  fi

  sudo tee "${service_file}" >/dev/null <<EOF
[Unit]
Description=Python Auto Build Worker FOR ${service_suffix}
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${work_dir}
ExecStart=${exec_start}
Restart=on-failure
RestartSec=30
KillMode=control-group
TimeoutStopSec=300

[Install]
WantedBy=multi-user.target
EOF

  sudo systemctl daemon-reload
  sudo systemctl enable "${service_name}"
  sudo systemctl restart "${service_name}"

  cat <<EOF

服务已启动。
查看状态：sudo systemctl status ${service_name}
查看日志：journalctl -u ${service_name} -f
EOF
}

main "$@"
