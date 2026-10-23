"""T6 可控混音与并发：真实链路预检能区分能力；不可用组合发布前失败；
LUFS/TP 可实测；并发默认 1。"""
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import common  # noqa: E402
import render  # noqa: E402
from conftest import full_ffmpeg  # noqa: E402


BUNDLED = os.path.join(common.REMOTION_DIR, "node_modules", "@remotion",
                       "compositor-win32-x64-msvc", "ffmpeg.exe")


def test_probe_discriminates_full_vs_bundled():
    """链路预检必须能区分完整构建与精简构建（E9：不能拿'能找到 exe'当混音可用）。"""
    ff = full_ffmpeg()
    if ff is None:
        pytest.skip("无完整 ffmpeg")
    ok, detail = common.probe_mix_chain(ff)
    assert ok, f"完整 ffmpeg 应通过混音链路预检: {detail}"
    if os.path.exists(BUNDLED):
        ok2, _ = common.probe_mix_chain(BUNDLED)
        assert not ok2, "Remotion 精简构建不应通过闪避链路预检"


def test_ffmpeg_path_require_mix_rejects_bundled_only(monkeypatch):
    """require_mix=True 时，若所有候选都不支持链路，必须报错而不是静默回退。"""
    monkeypatch.setattr(common, "_FFMPEG_FULL_CACHE", None)
    monkeypatch.setattr(common, "FFMPEG_CANDIDATES", (BUNDLED,))
    with pytest.raises(FileNotFoundError):
        common.ffmpeg_path(require_mix=True)


def test_ffmpeg_path_require_mix_prefers_chain_capable():
    """require_mix=True 必须返回通过链路预检的 ffmpeg。"""
    if full_ffmpeg() is None:
        pytest.skip("无完整 ffmpeg")
    common._FFMPEG_FULL_CACHE = None
    try:
        ff = common.ffmpeg_path(require_mix=True)
        ok, _ = common.probe_mix_chain(ff)
        assert ok
    finally:
        common._FFMPEG_FULL_CACHE = None


def test_measure_loudness_returns_lufs_tp(tmp_path):
    """LUFS/TP 实测：合成 1kHz 正弦 wav，返回合理量纲的测量值。"""
    if full_ffmpeg() is None:
        pytest.skip("无完整 ffmpeg")
    import wave
    import numpy as np
    wav = str(tmp_path / "tone.wav")
    t = np.linspace(0, 3.0, int(24000 * 3.0), endpoint=False)
    pcm = (np.sin(2 * np.pi * 1000 * t) * 12000).astype(np.int16)
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm.tobytes())
    m = common.measure_loudness(wav)
    assert m is not None, "loudnorm 分析失败"
    assert "integrated_lufs" in m and "true_peak_dbtp" in m
    # 12k 振幅正弦 ≈ -10.6 dBFS 峰值；综合响度应在 -25 ~ 0 LUFS 之间
    assert -30 < m["integrated_lufs"] < 0
    assert m["true_peak_dbtp"] < 0


def test_mix_preflight_blocks_when_unavailable(monkeypatch):
    """bgm 开启但链路不可用 → 渲染前失败；--no-bgm 时放行（loudnorm 可用即可）。"""
    def no_chain(path):
        return False, "mock: chain unavailable"

    monkeypatch.setattr(common, "probe_mix_chain", no_chain)
    ok, msg = render.check_mix_preflight(bgm_enabled=True, ff="fake.exe")
    assert not ok, "BGM 模式在链路不可用时必须发布前失败"

    # loudnorm 可用 → --no-bgm 放行
    monkeypatch.setattr(common, "probe_loudnorm",
                        lambda path: (True, "mock ok"))
    ok, msg = render.check_mix_preflight(bgm_enabled=False, ff="fake.exe")
    assert ok


def test_concurrency_default_is_one():
    """本机 OOM 记录后并发默认 1（E3/T6）。"""
    assert common.CONCURRENCY == 1
    src = open(os.path.join(os.path.dirname(common.SCRIPTS_DIR, "scripts") if False else
                            os.path.dirname(os.path.abspath(common.__file__)),
                            "run_all.py"), encoding="utf-8").read()
    m = re.search(r'--concurrency",\s*type=int,\s*default=(\d+)', src)
    assert m and m.group(1) == "1", "run_all 默认并发应为 1"


def test_render_state_includes_lufs(tmp_path):
    """write_render_state 输出必须含响度字段（未测为 None，不得填假数据）。"""
    state = render.write_render_state(
        str(tmp_path), "2026-10-14", str(tmp_path / "v.mp4"),
        bgm_path="", mix_ok=True, mix_mode="lufs_only",
        loudness={"integrated_lufs": -14.2, "true_peak_dbtp": -1.1},
    )
    import json
    data = json.load(open(state, encoding="utf-8"))
    assert data["audio_mix"]["mode"] == "lufs_only"
    assert data["loudness"]["integrated_lufs"] == -14.2
    assert data["loudness"]["true_peak_dbtp"] == -1.1
