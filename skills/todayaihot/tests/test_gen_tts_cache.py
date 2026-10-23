"""T4 TTS 缓存完整性：同文本同配置复用；改字/音色/语速失效；静音失败不进缓存。"""
import json
import os
import sys
import wave

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import write_json  # noqa: E402

import gen_tts  # noqa: E402
import tts_backend  # noqa: E402


class FakeSynth:
    """记录调用次数，可注入失败的假 TTS。"""

    def __init__(self):
        self.calls = []          # [(text, backend, speech_rate, loudness_rate)]
        self.fail_texts = set()

    def __call__(self, text, wav_path, backend="edge", speech_rate=0,
                 loudness_rate=0, emotion="neutral", return_timing=False):
        self.calls.append((text, backend, speech_rate, loudness_rate))
        if text in self.fail_texts:
            raise RuntimeError("模拟 TTS 失败")
        # 写一段 1s 假音频
        pcm = (np.ones(24000, dtype=np.int16) * 8000)
        with wave.open(wav_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm.tobytes())
        if return_timing:
            return [{"text": text[:1], "offset_sec": 0.0, "duration_sec": 0.5}]
        return []


@pytest.fixture()
def env(tmp_path, monkeypatch):
    fake = FakeSynth()
    monkeypatch.setattr(tts_backend, "synth", fake)
    monkeypatch.setattr(tts_backend, "choose_backend", lambda p="auto": "edge")
    monkeypatch.setattr(gen_tts.time, "sleep", lambda s: None)

    audio_dir = os.path.join(str(tmp_path), "work", "audio")
    public_dir = os.path.join(str(tmp_path), "public", "audio")
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(public_dir, exist_ok=True)
    monkeypatch.setattr(gen_tts, "AUDIO_DIR", audio_dir)
    monkeypatch.setattr(gen_tts, "PUBLIC_AUDIO", os.path.join(public_dir, "master.wav"))
    return fake, audio_dir, str(tmp_path)


def _narration(date="2026-10-14"):
    return {
        "date": date, "title": "每日 AI 头条", "total": 2,
        "scenes": [
            {"id": "s0_hook", "visual": {"type": "news_hook"},
             "clauses": ["今天 AI 圈有大事。"]},
            {"id": "s1_item", "visual": {"type": "news_item"},
             "clauses": ["第一条口播句。", "第二条口播句。"]},
        ],
    }


def _run(env, tmp_path, narration=None, force=False, speech_rate=None):
    fake, audio_dir, d = env
    narration = narration or _narration()
    npath = write_json(os.path.join(d, "narration.json"), narration)
    tpath = os.path.join(d, "timeline.json")
    argv = ["gen_tts.py", "--narration", npath, "--timeline", tpath]
    if force:
        argv.append("--force")
    old = sys.argv
    sys.argv = argv
    try:
        rc = gen_tts.main()
    finally:
        sys.argv = old
    return rc, tpath


def test_same_text_config_reuses_cache(env, tmp_path):
    fake, _, _ = env
    _run(env, tmp_path)
    n1 = len(fake.calls)
    _run(env, tmp_path)
    assert len(fake.calls) == n1, "同文本同配置必须命中缓存，不得重复合成"


def test_text_change_invalidates_cache(env, tmp_path):
    fake, _, _ = env
    _run(env, tmp_path)
    n1 = len(fake.calls)
    narr = _narration()
    narr["scenes"][1]["clauses"][0] = "改过之后的第一条口播句。"
    _run(env, tmp_path, narration=narr)
    assert len(fake.calls) == n1 + 1, "改字后必须只重合成改动的那一句"
    assert fake.calls[-1][0] == "改过之后的第一条口播句。"


def test_speech_rate_change_invalidates_cache(env, tmp_path, monkeypatch):
    fake, _, _ = env
    _run(env, tmp_path)
    n1 = len(fake.calls)
    monkeypatch.setattr(gen_tts, "SPEECH_RATE", 45)   # 模拟改语速
    _run(env, tmp_path)
    assert len(fake.calls) == n1 + len(_narration()["scenes"][1]["clauses"]) + 1, \
        "语速变化必须使全部缓存失效"
    assert all(c[2] == 45 for c in fake.calls[n1:])


def test_silent_failure_not_cached_as_success(env, tmp_path):
    """TTS 失败的句子：静音占位不得成为可复用缓存；修复后重试应得到真实词边界。"""
    fake, audio_dir, _ = env
    fake.fail_texts.add("第一条口播句。")
    rc, tpath = _run(env, tmp_path)
    assert rc == 0
    tl = json.load(open(tpath, encoding="utf-8"))
    assert tl["failed_clauses"], "失败句必须记入 failed_clauses"
    clause = tl["scenes"][1]["clauses"][0]
    assert clause["timing_src"] == "silent_fallback"
    # 失败句的 wav 不得作为成功缓存残留
    wav = os.path.join(audio_dir, "s1_item_00.wav")
    assert not os.path.exists(wav), "失败句不得留下可复用的 wav 缓存"

    # 后端恢复：不加 --force 重跑，失败句应被自动重试
    fake.fail_texts.clear()
    rc, tpath = _run(env, tmp_path)
    assert rc == 0
    tl = json.load(open(tpath, encoding="utf-8"))
    assert not tl["failed_clauses"], "恢复后重试应成功"
    clause = tl["scenes"][1]["clauses"][0]
    assert clause["timing_src"] == "word", "重试成功必须是词边界计时，不能伪装成 even"
    assert clause["chars"], "词边界必须产出逐字时间戳"


def test_force_resynthesizes(env, tmp_path):
    fake, _, _ = env
    _run(env, tmp_path)
    n1 = len(fake.calls)
    _run(env, tmp_path, force=True)
    assert len(fake.calls) == n1 + 3, "--force 应全量重合成"


def test_only_failed_clause_regenerated(env, tmp_path):
    """只重生成失效句：好句命中缓存，不被 force 式全量重来。"""
    fake, _, _ = env
    # 首轮即失败：好句正常缓存，坏句不落缓存（fake 内部重试 4 次）
    fake.fail_texts.add("第二条口播句。")
    rc, tpath = _run(env, tmp_path)
    assert rc == 0
    tl = json.load(open(tpath, encoding="utf-8"))
    assert len(tl["failed_clauses"]) == 1
    n2 = len(fake.calls)
    # 修复后重跑（不加 --force）：仅失败句重新合成
    fake.fail_texts.clear()
    _run(env, tmp_path)
    assert len(fake.calls) == n2 + 1, "只应重合成此前失败的那一句"
    tl = json.load(open(tpath, encoding="utf-8"))
    assert not tl["failed_clauses"]
    assert tl["scenes"][1]["clauses"][0]["timing_src"] == "word"
    assert tl["scenes"][1]["clauses"][1]["timing_src"] == "word"
