"""T5 时间基准与片尾契约：

1. 时间映射不变量（Python 侧合成 fixture）：
   master.wav = [TITLE_PAD 静音][逐句 PCM]，clause.start = TITLE_PAD + 游标；
   音频从第 0 帧起播时，wav 位置 == 视频时间，字幕起点与首字发声误差 ≤ 1 帧。
2. TSX 源码契约（跨语言锁定，防止单侧改动破坏映射）：
   - Audio 必须从第 0 帧起播（不得再套 Sequence 延迟）；
   - 末场景必须覆盖 master_duration + TAIL_BUFFER（无纯背景空尾）；
   - TITLE_PAD * FPS == TITLE_CARD_FRAMES（Python 与前端常量一致）。
"""
import os
import re
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from common import FPS, TITLE_PAD  # noqa: E402
import gen_tts  # noqa: E402

REMOTION_SRC = os.path.abspath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "remotion", "src"))
NEWSVIDEO_TSX = os.path.join(REMOTION_SRC, "NewsVideo.tsx")
VIDEOCONFIG_TS = os.path.join(REMOTION_SRC, "videoConfig.ts")


def _make_beep_pcm(seconds=1.0, freq=880, rate=24000):
    t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
    return (np.sin(2 * np.pi * freq * t) * 12000).astype(np.int16)


def test_title_pad_matches_title_card_frames():
    """Python 的 TITLE_PAD 与前端 TITLE_CARD_FRAMES 必须是同一段时间。"""
    src = open(VIDEOCONFIG_TS, encoding="utf-8").read()
    m = re.search(r"TITLE_CARD_FRAMES\s*=\s*(\d+)", src)
    assert m, "videoConfig.ts 缺少 TITLE_CARD_FRAMES"
    assert round(TITLE_PAD * FPS) == int(m.group(1)), \
        "TITLE_PAD*FPS 与 TITLE_CARD_FRAMES 不一致：静音被双计或缺失"


def _build_fixture(tmp_wav):
    """合成 master：0.1s 静音 + 两句哔声（各 1s），clause.start 含 TITLE_PAD。"""
    pcm1, pcm2 = _make_beep_pcm(), _make_beep_pcm(freq=1320)
    master = np.concatenate([np.zeros(int(24000 * TITLE_PAD), dtype=np.int16), pcm1, pcm2])
    with wave.open(tmp_wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(master.tobytes())
    cursor = 0.0
    clauses = []
    for pcm in (pcm1, pcm2):
        dur = len(pcm) / 24000
        clauses.append({
            "text": "哔。", "start": round(TITLE_PAD + cursor, 4),
            "end": round(TITLE_PAD + cursor + dur, 4), "duration": round(dur, 4),
            "chars": [{"ch": "哔", "t": 0.0}, {"ch": "。", "t": dur * 0.9}],
        })
        cursor += dur
    return master, clauses


def test_beep_onset_maps_within_one_frame(tmp_path):
    """点击声 fixture：句起点（含 TITLE_PAD）在 wav 中的位置 == start，
    音频 0 帧起播时对应视频帧 = round(start*FPS)，误差 ≤ 1 帧。"""
    wav = str(tmp_path / "master.wav")
    master, clauses = _build_fixture(wav)
    total = len(master) / 24000
    for c in clauses:
        onset_frame = round(c["start"] * FPS)
        exact = c["start"] * FPS
        assert abs(onset_frame - exact) <= 0.5 + 1e-9, "句起点取整误差超过半帧"
        # wav 位置验证：start 处应是哔声（非静音）
        pos = int(c["start"] * 24000)
        seg = master[pos:pos + 2400].astype(np.float64)
        rms = float(np.sqrt(np.mean(seg ** 2)))
        assert rms > 1000, f"clause.start={c['start']} 处 wav 是静音，映射断裂"
    assert abs(total - (TITLE_PAD + 2.0)) < 0.01


def test_chars_invariants_preserved():
    """现有字幕相对时间不变量：chars 单调不减、不越句长（回归保护）。"""
    text = "这是一句测试口播，包含 English 和 数字 123。"
    dur = 3.0
    bounds = [
        {"text": "这是", "offset_sec": 0.0, "duration_sec": 0.2},
        {"text": "一句", "offset_sec": 0.4, "duration_sec": 0.2},
        {"text": "English", "offset_sec": 0.9, "duration_sec": 0.5},
        {"text": "123", "offset_sec": 1.8, "duration_sec": 0.4},
    ]
    chars = gen_tts.finalize_chars(gen_tts.build_chars_from_bounds(text, bounds, dur), dur)
    ts = [c["t"] for c in chars]
    assert all(0.0 <= t <= dur for t in ts), "字时标越界"
    assert all(a <= b for a, b in zip(ts, ts[1:])), "字时标逆序"
    assert ts == sorted(ts)


def test_tsx_audio_starts_at_frame_zero():
    """TSX 契约：Audio 不得再套延迟 Sequence（E10 静音双计回归锁）。"""
    src = open(NEWSVIDEO_TSX, encoding="utf-8").read()
    m = re.search(r"<Audio\s+src=\{audioSrc\}\s*/>", src)
    assert m, "NewsVideo.tsx 缺少 <Audio src={audioSrc} />"
    prefix = src[:m.start()]
    tail = prefix[-300:]
    assert "<Sequence" not in tail, \
        "Audio 被包进延迟 Sequence：master 已含 TITLE_PAD 静音，再延迟会双计（E10）"


def test_tsx_last_scene_covers_tail_buffer():
    """TSX 契约：末场景 endSec 必须到 masterDur + TAIL_BUFFER（E11 空尾回归锁）。"""
    src = open(NEWSVIDEO_TSX, encoding="utf-8").read()
    assert "masterDur + TAIL_BUFFER_FRAMES / VIDEO_FPS" in src, \
        "末场景未覆盖尾部缓冲，缓冲区将呈现纯背景空尾"
    imports = re.findall(r"import\s*\{[^}]*\}", src)
    assert any("TAIL_BUFFER_FRAMES" in im for im in imports), \
        "NewsVideo.tsx 未导入 TAIL_BUFFER_FRAMES"
    # 旧的「末场景止于最后一个 clause.end」写法必须消失
    assert "s.clauses[s.clauses.length - 1].end" not in src
