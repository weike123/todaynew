"""todayaihot 依赖检查脚本。

被 run_all.py 在启动时调用，确保核心依赖齐全。
缺失时打印明确的安装命令，避免运行到一半才报 ImportError。

用法:
    python check_deps.py [--strict]   # --strict：可选依赖缺失也报错
"""
import importlib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 核心依赖：(import 名, pip 包名, 最低版本或 None)
CORE_DEPS = [
    ("requests", "requests", None),
    ("bs4", "beautifulsoup4", None),
    ("lxml", "lxml", None),
    ("PIL", "pillow", None),
    ("numpy", "numpy", None),
    ("edge_tts", "edge-tts", None),
    ("websocket", "websocket-client", None),
]

# 可选依赖：缺失时降级而非报错
OPTIONAL_DEPS = [
    ("faster_whisper", "faster-whisper", "Whisper 强制对齐（volc/gptsovits 逐字字幕）"),
]


def _check_one(mod_name: str, pkg_name: str):
    """返回 (ok, version_or_error)。"""
    try:
        mod = importlib.import_module(mod_name)
        ver = getattr(mod, "__version__", "?")
        # PIL 的版本在 PIL.__version__
        if mod_name == "PIL":
            from PIL import Image
            ver = getattr(Image, "__version__", "?")
        return True, ver
    except ImportError as e:
        return False, str(e)


def main():
    strict = "--strict" in sys.argv
    errors = []
    warnings = []

    print("[check_deps] 核心依赖检查...")
    for mod_name, pkg_name, _ in CORE_DEPS:
        ok, info = _check_one(mod_name, pkg_name)
        if ok:
            print(f"  ✓ {pkg_name:25s} {info}")
        else:
            errors.append(f"  ✗ {pkg_name:25s} 缺失: {info}")

    print("[check_deps] 可选依赖检查...")
    for mod_name, pkg_name, desc in OPTIONAL_DEPS:
        ok, info = _check_one(mod_name, pkg_name)
        if ok:
            print(f"  ✓ {pkg_name:25s} {info}  ({desc})")
        else:
            warnings.append(f"  ⚠ {pkg_name:25s} 未安装 ({desc})，将降级")

    # ffmpeg 检查（Remotion 自带）+ 混音链路能力报告（T6/E9）
    try:
        from common import ffmpeg_path, probe_loudnorm, probe_mix_chain
        ff = ffmpeg_path()
        print(f"  ✓ ffmpeg                   {ff}")
        ok_ln, _ = probe_loudnorm(ff)
        print(f"  {'✓' if ok_ln else '✗'} ffmpeg loudnorm          "
              f"{'可用' if ok_ln else '不可用（--no-bgm 也会失败）'}")
        ok_mix, _ = probe_mix_chain(ff)
        if ok_mix:
            print("  ✓ ffmpeg 闪避混音链路      可用（asplit/aloop/sidechaincompress/amix/loudnorm）")
        else:
            print("  ⚠ ffmpeg 闪避混音链路      不可用：BGM 模式会在渲染前失败；"
                  "可设 TODAYAIHOT_FFMPEG 指向完整构建或用 --no-bgm")
    except Exception as e:
        errors.append(f"  ✗ ffmpeg                   未找到: {e}")

    if warnings:
        print("\n[check_deps] 可选依赖缺失（不影响核心流程）:")
        for w in warnings:
            print(w)
        print(f"  安装: {sys.executable} -m pip install faster-whisper")

    if errors:
        print("\n[check_deps] 核心依赖缺失，无法继续:")
        for e in errors:
            print(e)
        pkgs = " ".join(p for _, p, _ in CORE_DEPS)
        print(f"\n  一键安装: {sys.executable} -m pip install {pkgs}")
        return 1

    if strict and warnings:
        print("\n[check_deps] --strict 模式下可选依赖缺失视为错误")
        return 1

    print("\n[check_deps] 全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
