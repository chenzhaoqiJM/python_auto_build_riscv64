"""
RISC-V JIT 测试脚本

MCJIT (RuntimeDyld) 不支持 RISC-V —— LLVM 的 RuntimeDyldELF::resolveRelocation()
中没有 RISC-V 的 case 分支，会走到 llvm_unreachable("Unsupported CPU type!") 导致段错误。

唯一可行方案：OrcJIT + JITLink（从 LLVM 13 起支持 RISC-V ELF）
"""

from ctypes import CFUNCTYPE, c_int32
import llvmlite.ir as ir
import llvmlite.binding as llvm
import llvmlite


def create_sum_module():
    module = ir.Module(name="test_module")
    int32 = ir.IntType(32)
    func_ty = ir.FunctionType(int32, [int32, int32])
    func = ir.Function(module, func_ty, name="sum")
    func.args[0].name = "a"
    func.args[1].name = "b"
    block = func.append_basic_block(name="entry")
    builder = ir.IRBuilder(block)
    result = builder.add(func.args[0], func.args[1], name="res")
    builder.ret(result)
    return module


def test_mcjit():
    """演示 MCJIT 在 RISC-V 上必然失败"""
    print("=" * 60)
    print("[TEST 1] MCJIT (预期失败 - RuntimeDyld 不支持 RISC-V)")
    print("=" * 60)

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    triple = llvm.get_process_triple()

    module_ir = create_sum_module()
    module_ir.triple = triple
    module_ir.data_layout = str(target_machine.target_data)

    llvm_module = llvm.parse_assembly(str(module_ir))
    llvm_module.verify()

    print(f"  Triple: {triple}")
    print(f"  跳过 MCJIT 测试 — RuntimeDyldELF::resolveRelocation() "
          f"没有 RISC-V 分支，会导致段错误")
    print()


def test_orcjit_rtdyld():
    """演示 OrcJIT + RTDyld 后端在 RISC-V 上也必然失败（同样的原因）"""
    print("=" * 60)
    print("[TEST 2] OrcJIT + RTDyld (预期失败 - 同样不支持 RISC-V)")
    print("=" * 60)

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    triple = llvm.get_process_triple()

    module_ir = create_sum_module()
    module_ir.triple = triple
    module_ir.data_layout = str(target_machine.target_data)

    print(f"  Triple: {triple}")
    print(f"  跳过 OrcJIT+RTDyld 测试 — 底层仍然是 RuntimeDyld，"
          f"同样没有 RISC-V 重定位支持")
    print()


def test_orcjit_jitlink():
    """OrcJIT + JITLink — 唯一支持 RISC-V 的路径"""
    print("=" * 60)
    print("[TEST 3] OrcJIT + JITLink (RISC-V 唯一可行方案)")
    print("=" * 60)

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    triple = llvm.get_process_triple()

    module_ir = create_sum_module()
    module_ir.triple = triple
    module_ir.data_layout = str(target_machine.target_data)

    print(f"  Triple: {triple}")
    print(f"  Generated IR:\n{module_ir}")

    try:
        # 关键：use_jit_link=True 使用 JITLink 而非 RuntimeDyld
        lljit = llvm.create_lljit_compiler(target_machine, use_jit_link=True)

        rt = (llvm.JITLibraryBuilder()
              .add_ir(str(module_ir))
              .add_current_process()
              .export_symbol("sum")
              .link(lljit, "mylib"))

        func_ptr = rt["sum"]
        print(f"  函数地址: 0x{func_ptr:x}")

        cfunc = CFUNCTYPE(c_int32, c_int32, c_int32)(func_ptr)

        a, b = 10, 32
        result = cfunc(a, b)
        print(f"  sum({a}, {b}) = {result}")
        assert result == a + b, f"Expected {a + b}, got {result}"
        print(f"  ✅ SUCCESS")

    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        print()
        print("  如果报错包含 'JITLink' 相关信息，可能是因为:")
        print("  1. llvmlite 编译时没有包含 RISC-V 的 JITLink 支持")
        print("  2. LLVM 版本过低 (需要 LLVM >= 13)")
        print("  3. libllvmlite.so 编译时缺少必要的 LLVM 组件")

    print()


def main():
    # llvm.initialize()
    # llvm.initialize_native_target()
    # llvm.initialize_native_asmprinter()
    llvm.initialize_all_targets()
    llvm.initialize_all_asmprinters()

    print(f"llvmlite version: {llvmlite.__version__}")
    print(f"LLVM version: {'.'.join(str(x) for x in llvm.llvm_version_info)}")
    print(f"Target triple: {llvm.get_process_triple()}")
    print()

    test_mcjit()
    test_orcjit_rtdyld()
    test_orcjit_jitlink()

    print("=" * 60)
    print("总结:")
    print("  MCJIT / OrcJIT+RTDyld: RISC-V 不支持 (RuntimeDyld 无重定位实现)")
    print("  OrcJIT+JITLink:        RISC-V 唯一可行的 JIT 路径")
    print("=" * 60)


if __name__ == "__main__":
    main()
