import requests
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
import os

BUILD_FOR_VERSION = os.getenv("BUILD_FOR_VERSION")   # 如果不存在则返回 None

if len(sys.argv) < 2:
    print("Usage: python 00get_pkg_version.py <package_name>")
    sys.exit(1)

package_name = sys.argv[1]
two_years_ago = datetime.now() - timedelta(days=365)

py_version = sys.version_info

# 根据 Python 版本决定 how_years_ago
if BUILD_FOR_VERSION == "3.9":
    print("🚀 [Python 3.9] 支持周期: 2020-10-05 → 2025-10-01")
    lower_bound = datetime(2020, 10, 5)  # 3.9.0 正式发布日
    upper_bound = datetime(2025, 10, 1)  # EOL（官方公布）
# if (py_version.major, py_version.minor) == (3, 10):
elif BUILD_FOR_VERSION == "3.10":
    print("🚀 [Python 3.10] 支持周期: 2021-10-04 → 2026-10-01")
    lower_bound = datetime(2021, 10, 4)  # 3.10.0 正式发布日
    upper_bound = datetime(2026, 10, 1)  # EOL（预计）

elif BUILD_FOR_VERSION == "3.11":
    print("🚀 [Python 3.11] 支持周期: 2022-10-04 → 2027-10-01")
    lower_bound = datetime(2022, 10, 4)  # 3.10.0 正式发布日
    upper_bound = datetime(2027, 10, 1)  # EOL（预计）

elif BUILD_FOR_VERSION == "3.12":
    lower_bound = datetime(2023, 8, 2)  # 3.12.0 正式发布日,提前
    upper_bound = datetime(2028, 10, 1)  # EOL（预计）
    print("🚀 [Python 3.12] 支持周期: 2023-08-02 → 2028-10-01")

elif BUILD_FOR_VERSION == "3.13":
    lower_bound = datetime(2024, 6, 1)  # 3.13 发布日，提前
    upper_bound = datetime(2029, 10, 1)  # EOL（预计）
    print("🚀 [Python 3.13] 支持周期: 2024-06-01 → 2029-10-01")
elif BUILD_FOR_VERSION == "3.13t":
    lower_bound = datetime(2024, 6, 1)  # 3.13 发布日，提前
    upper_bound = datetime(2029, 10, 1)  # EOL（预计）
    print("🚀 [Python 3.13t] 支持周期: 2024-06-01 → 2029-10-01")
elif BUILD_FOR_VERSION == "3.14":
    lower_bound = datetime(2025, 4, 1)  # 3.13 发布日，提前
    upper_bound = datetime(2030, 10, 1)  # EOL（预计）
    print("🚀 [Python 3.14] 支持周期: 2025-06-01 → 2030-10-01")
elif BUILD_FOR_VERSION == "3.14t":
    lower_bound = datetime(2025, 4, 1)  # 3.13 发布日，提前
    upper_bound = datetime(2030, 10, 1)  # EOL（预计）
    print("🚀 [Python 3.14t] 支持周期: 2025-06-01 → 2030-10-01")
else:
    # 默认 3 年窗口
    lower_bound = datetime.now() - timedelta(days=365*3)
    upper_bound = datetime.now()

url = f"https://pypi.org/pypi/{package_name}/json"

# 配置重试策略
session = requests.Session()
retries = Retry(
    total=10,
    backoff_factor=2,  # 指数退避 (1s, 2s, 4s, 8s ...)
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
session.mount("https://", HTTPAdapter(max_retries=retries))

try:
    response = session.get(url, timeout=10)
    response.raise_for_status()
except requests.RequestException as e:
    print(f"Error: Failed to fetch data for package {package_name} - {e}")
    sys.exit(1)

data = response.json()

releases = data['releases']
recent_versions = set()

for version, release_info in releases.items():
    for release in release_info:
        release_date = release['upload_time']
        release_datetime = datetime.strptime(release_date, '%Y-%m-%dT%H:%M:%S')
        
        # if release_datetime > two_years_ago:
        if lower_bound <= release_datetime <= upper_bound:
            recent_versions.add(version)

sorted_versions = sorted(recent_versions, reverse=True)
file_name = f"{package_name}.log"
with open(file_name, 'w') as f:
    for version in sorted_versions:
        f.write(f"{version}\n")

print(f"Versions for {package_name} have been written to {file_name}")
