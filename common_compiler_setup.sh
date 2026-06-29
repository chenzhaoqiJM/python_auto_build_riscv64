#!/usr/bin/env bash

# 公共编译器检查和切换逻辑。
# 约定调用方可提供 log_step/log_info/run_and_log；若未提供，则使用默认实现。

if ! declare -F log_step >/dev/null 2>&1; then
	log_step() {
		echo
		echo "-- $*"
	}
fi

if ! declare -F log_info >/dev/null 2>&1; then
	log_info() {
		echo "   $*"
	}
fi

if ! declare -F run_and_log >/dev/null 2>&1; then
	run_and_log() {
		printf '   $'
		printf ' %q' "$@"
		printf '\n'
		"$@"
	}
fi

ensure_gcc_14() {
	log_step "检查 GCC 版本"

	local gcc_major
	gcc_major=$(gcc -dumpfullversion | cut -d. -f1)
	log_info "当前 gcc: $(gcc --version | head -n 1)"

	if [ "$gcc_major" -lt 14 ]; then
		log_info "当前 GCC 主版本为 $gcc_major，小于 14，开始安装 gcc-14 和 g++-14"

		run_and_log sudo apt install -y gcc-14 g++-14

		# 设置 update-alternatives
		run_and_log sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-14 100
		run_and_log sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-14 100
		run_and_log sudo update-alternatives --set gcc /usr/bin/gcc-14
		run_and_log sudo update-alternatives --set g++ /usr/bin/g++-14

		run_and_log sudo update-alternatives --install /usr/bin/riscv64-linux-gnu-gcc riscv64-linux-gnu-gcc /usr/bin/riscv64-linux-gnu-gcc-14 100
		run_and_log sudo update-alternatives --install /usr/bin/riscv64-linux-gnu-g++ riscv64-linux-gnu-g++ /usr/bin/riscv64-linux-gnu-g++-14 100
		run_and_log sudo update-alternatives --set riscv64-linux-gnu-gcc /usr/bin/riscv64-linux-gnu-gcc-14
		run_and_log sudo update-alternatives --set riscv64-linux-gnu-g++ /usr/bin/riscv64-linux-gnu-g++-14

		log_info "✅ GCC/G++ 已切换为 14"
	else
		log_info "✅ 当前 GCC 主版本为 $gcc_major，已满足 ≥ 14，无需切换"
	fi

	log_info "生效 gcc: $(gcc --version | head -n 1)"
	log_info "生效 g++: $(g++ --version | head -n 1)"
}

ensure_gfortran_14() {
	log_step "检查 GFortran 版本"

	local gfortran_major
	gfortran_major=$(gfortran -dumpfullversion | cut -d. -f1)
	log_info "当前 gfortran: $(gfortran --version | head -n 1)"

	if [ "$gfortran_major" -lt 14 ]; then
		log_info "当前 GFortran 主版本为 $gfortran_major，小于 14，开始安装 gfortran-14"
		run_and_log sudo apt install gfortran-14
		run_and_log sudo update-alternatives --install /usr/bin/gfortran gfortran /usr/bin/gfortran-14 140
		run_and_log sudo update-alternatives --set gfortran /usr/bin/gfortran-14

		run_and_log sudo update-alternatives --install /usr/bin/riscv64-linux-gnu-gfortran riscv64-linux-gnu-gfortran /usr/bin/riscv64-linux-gnu-gfortran-14 140
		run_and_log sudo update-alternatives --set riscv64-linux-gnu-gfortran /usr/bin/riscv64-linux-gnu-gfortran-14

		log_info "✅ GFortran 已切换为 14"
	else
		log_info "✅ 当前 GFortran 主版本为 $gfortran_major，已满足 ≥ 14，无需切换"
	fi

	log_info "生效 gfortran: $(gfortran --version | head -n 1)"
}

ensure_compilers_14() {
	ensure_gcc_14
	ensure_gfortran_14
}
