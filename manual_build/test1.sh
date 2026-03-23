TO_BUILD_VERSIONS=("2.8.0" "2.7.1" "2.7.0" "2.6.0" "2.5.1" "2.5.0" "2.4.1" "2.4.0" "2.3.1" "2.3.0" "2.2.2" "2.2.1" "2.2.0")

for v in "${TO_BUILD_VERSIONS[@]}"; do
    # 比较 v < 2.5.0
    if [ "$(printf '%s\n%s\n' "$v" "2.5.0" | sort -V | head -n1)" = "$v" ] && [ "$v" != "2.5.0" ]; then
        export USE_SYSTEM_SLEEF=ON
    else
        unset USE_SYSTEM_SLEEF  # 或者保持默认
    fi

    echo "Building version $v (USE_SYSTEM_SLEEF=${USE_SYSTEM_SLEEF:-OFF})"
    # 在这里调用你的构建脚本
done
