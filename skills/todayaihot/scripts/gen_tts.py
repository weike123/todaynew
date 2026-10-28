"""narration.json -> 逐句配音 wav + master.wav + timeline.json（KTV 字幕时间轴）

用法:
    python gen_tts.py [--narration work/narration.json] [--force]

环节:
    1. 逐句调用火山 seed-tts-2.0 合成 wav（语速 +30% / 音量 +50%）
    2. 响度归一化（浮点中间量，避免 int16 截断成静音）
    3. 拼接 master.wav（前置 0.1s 静音供标题卡）
    4. 生成 timeline.json：句级时间戳 + 每字 KTV 时间戳
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    AUDIO_DIR, NARRATION, PUBLIC_AUDIO, SAMPLE_RATE, SPEECH_RATE,
    LOUDNESS_RATE, TARGET_RMS, TIMELINE, TITLE_PAD, WORK_DIR, ensure_dirs,
    sha256_file,
)
import tts_backend  # noqa: E402


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SAMPLE_RATE, f"{path} 采样率异常"
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def normalize(data: np.ndarray) -> np.ndarray:
    """响度归一：必须走浮点中间量，直接 data*gain 会把小振幅截断为 0（整轨静音）。"""
    if data.size == 0:
        return data
    x = data.astype(np.float64)
    rms = np.sqrt(np.mean(x ** 2))
    if rms > 0:
        gain = min(TARGET_RMS * 32767.0 / rms, 20.0)
        x = x * gain
    peak = np.max(np.abs(x))
    if peak > 32000:                      # 防削波
        x = x * (32000.0 / peak)
    return np.clip(x, -32767, 32767).astype(np.int16)


def cache_fingerprint(text: str, backend: str,
                      speech_rate: int = SPEECH_RATE,
                      loudness_rate: int = LOUDNESS_RATE,
                      voice: str = "") -> str:
    """缓存指纹：文本 + 后端 + 音色 + 语速 + 音量。任一变化必须使缓存失效（T4）。

    v3：音色纳入指纹（P2-1）——此前只绑后端名，换音色会错误复用旧 wav。
    voice 为空时按当前配置解析，保证旧调用方式也绑定实际音色。
    """
    import hashlib
    if not voice:
        voice = tts_backend.active_voice(backend)
    raw = f"v3|{backend}|{voice}|{speech_rate}|{loudness_rate}|{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_cache(cache_path: str) -> dict:
    try:
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _write_cache(cache_path: str, fp: str, bounds: list):
    tmp = cache_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"fp": fp, "bounds": bounds}, f, ensure_ascii=False)
    os.replace(tmp, cache_path)


def _invalidate(wav_path: str):
    """删除某句的 wav 与缓存（TTS 失败后调用，防止静音占位伪装成成功缓存）。"""
    for p in (wav_path, wav_path + ".cache.json", wav_path + ".bounds.json"):
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass


def synth_clause(text: str, wav_path: str, force: bool, backend: str,
                 speech_rate: int = SPEECH_RATE,
                 loudness_rate: int = LOUDNESS_RATE):
    """合成单句，返回 (归一化后时长秒, PCM 数据, 词边界列表)。

    缓存绑定「文本+后端+语速+音量」指纹（T4）：
    - 同文本同配置 → 复用已有 wav 与词边界（词边界随缓存文件一起存取，
      避免「缓存命中 → 退回均分时间戳」导致字幕漂移）；
    - 改字 / 换后端 / 改语速音量 → 指纹不符，自动重合成；
    - 合成失败 → 删除该句 wav 与缓存，静音占位只进内存（master 拼接用），
      绝不落盘为可复用缓存；下次运行自动重试该句。
    """
    cache_path = wav_path + ".cache.json"
    fp = cache_fingerprint(text, backend, speech_rate, loudness_rate)

    if not force and os.path.exists(wav_path) and os.path.getsize(wav_path) >= 1024:
        cache = _read_cache(cache_path)
        if cache.get("fp") == fp:
            bounds = cache.get("bounds", [])
            data = normalize(read_wav(wav_path))
            dur = len(data) / SAMPLE_RATE
            with wave.open(wav_path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(SAMPLE_RATE)
                w.writeframes(data.tobytes())
            return dur, data, bounds
        # 指纹不符（文本/配置已变）→ 作废旧缓存，走重合成
        _invalidate(wav_path)

    last_err = None
    for attempt in range(4):          # edge-tts 偶发限流/挂起，多试几次
        try:
            bounds = tts_backend.synth(
                text, wav_path, backend=backend,
                speech_rate=speech_rate,
                loudness_rate=loudness_rate,
                emotion="neutral",
                return_timing=True,
            ) or []
            last_err = None
            break
        except Exception as e:
            last_err = e
            print(f"    [retry {attempt + 1}/4] {type(e).__name__}: {str(e)[:90]}")
            time.sleep(2.0 * (attempt + 1))
    if last_err:
        # 失败必须清掉半成品，防止下次命中坏缓存
        _invalidate(wav_path)
        raise RuntimeError(f"TTS 失败（已重试 4 次）: {text[:20]}... -> {last_err}")
    time.sleep(0.25)
    _write_cache(cache_path, fp, bounds)

    data = normalize(read_wav(wav_path))
    dur = len(data) / SAMPLE_RATE
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(data.tobytes())
    return dur, data, bounds


def build_chars(text: str, dur: float):
    """句内按非空白字符均分时间戳（兜底方案，中英文混排时会漂移）。"""
    chars = [c for c in text if c.strip()] or [text]
    step = dur / len(chars)
    return [{"ch": c, "t": round(i * step, 4)} for i, c in enumerate(chars)]


def build_chars_from_bounds(text: str, bounds: list, dur: float):
    """用 edge-tts WordBoundary 的真实发音时间生成逐字时间戳。

    中英文/数字的发音速度差异很大，「均分」方案会让 KTV 高亮逐渐漂移
    （典型症状：视频 0:25 起字幕明显落后/超前配音）。词级边界覆盖不到的
    标点与空格，用前后词的时间插值补齐。
    """
    if not bounds:
        return build_chars(text, dur)
    n = len(text)
    times: list = [None] * n
    pos = 0
    for b in sorted(bounds, key=lambda x: x.get("offset", 0)):
        word = b.get("text") or ""
        if not word:
            continue
        # 兼容两种入参：带 offset_sec（tts_backend 产出）或裸 100ns 整数
        if "offset_sec" in b:
            start = float(b["offset_sec"])
            wdur = float(b.get("duration_sec", 0.0))
        else:
            start = float(b.get("offset", 0)) / 10_000_000.0
            wdur = float(b.get("duration", 0)) / 10_000_000.0
        idx = text.find(word, pos)
        if idx < 0:
            continue
        m = len(word)
        if m == 1:
            times[idx] = start
        else:
            for k in range(m):
                times[idx + k] = start + wdur * k / (m - 1)
        pos = idx + m
    if not any(t is not None for t in times):
        return build_chars(text, dur)
    # 标点/空格等未覆盖字符：向前取上一词尾，向后取下一词头，两者取中
    for i in range(n):
        if times[i] is not None:
            continue
        prev = next((times[j] for j in range(i - 1, -1, -1)
                     if times[j] is not None), None)
        nxt = next((times[j] for j in range(i + 1, n)
                    if times[j] is not None), None)
        if prev is not None and nxt is not None:
            times[i] = (prev + nxt) / 2
        elif nxt is not None:
            times[i] = nxt
        elif prev is not None:
            times[i] = prev
        else:
            times[i] = 0.0
    chars = [
        {"ch": ch, "t": round(max(0.0, min(t, dur)), 4)}
        for ch, t in zip(text, times)
        if ch.strip()
    ]
    return chars or build_chars(text, dur)


def finalize_chars(chars: list, dur: float) -> list:
    """尾部压缩：若最后一个字的发音时间晚于 0.9*dur，整轴等比压缩到 0.9*dur。

    KTV 字幕在句尾切换前进[count]入下一句，尾字（尤其句末标点）若时间戳
    太靠近句子结尾，观感上就是「尾部字幕一直不变色」。压缩后高亮会在
    句子结束前留出约 10% 的缓冲，且等比缩放对中段同步影响 <0.3s，无感知。
    """
    if not chars:
        return chars
    max_t = max(c["t"] for c in chars)
    limit = dur * 0.9
    if max_t > limit > 0:
        k = limit / max_t
        for c in chars:
            c["t"] = round(c["t"] * k, 4)
    # 保证单调不减
    prev = 0.0
    for c in chars:
        if c["t"] < prev:
            c["t"] = prev
        prev = c["t"]
    return chars


def main():
    ap = argparse.ArgumentParser(description="narration.json -> 配音 + 字幕时间轴")
    ap.add_argument("--narration", default=NARRATION)
    ap.add_argument("--timeline", default=TIMELINE)
    ap.add_argument("--force", action="store_true", help="强制重合成（忽略已有 wav）")
    ap.add_argument("--backend", default="edge",
                    choices=["auto", "volc", "edge", "gptsovits"],
                    help="TTS 后端：默认 edge（免费、稳定、无需 Key）；"
                         "auto=火山优先失败降级；volc=强制火山豆包 seed-tts-2.0；"
                         "gptsovits=本地 GPT-SoVITS v2Pro 零样本克隆（main 参考音频，需 9880 服务在线）")
    ap.add_argument("--align", default="auto",
                    choices=["auto", "edge", "whisper"],
                    help="字幕对齐方式：auto=edge后端用词边界、其他后端用Whisper；"
                         "edge=强制用TTS词边界；whisper=强制用faster-whisper逐词对齐")
    args = ap.parse_args()

    ensure_dirs()
    backend = tts_backend.choose_backend(args.backend)
    print(f"[tts] 语速 +{SPEECH_RATE}% / 音量 +{LOUDNESS_RATE}% / 后端 {backend}")
    with open(args.narration, "r", encoding="utf-8") as f:
        narration = json.load(f)

    scenes_out = []
    all_pcm = []
    cursor = 0.0                       # 内容时间（不含标题卡静音）
    n_ok = 0
    failed_clauses = []                # TTS 失败的句子（静音占位）

    for scene in narration["scenes"]:
        sc = {"id": scene["id"], "clauses": []}
        for ci, text in enumerate(scene["clauses"]):
            wav = os.path.join(AUDIO_DIR, f"{scene['id']}_{ci:02d}.wav")
            try:
                # 显式传语速/音量：默认参数在函数定义时绑定，改配置不会生效
                dur, data, bounds = synth_clause(
                    text, wav, args.force, backend,
                    speech_rate=SPEECH_RATE, loudness_rate=LOUDNESS_RATE,
                )
                timing_src = "word" if bounds else "even"
            except RuntimeError as e:
                # 单句 TTS 失败不中断整条流水线：静音占位只进内存（供 master 拼接），
                # 不落盘为缓存（T4：静音失败不能伪装成 word/even 成功缓存）。
                # 该句 wav 与缓存已被清除，下次运行自动重试，无需 --force 全量重来。
                est_dur = max(1.0, len(text) / 5.0 + 0.3)
                data = np.zeros(int(SAMPLE_RATE * est_dur), dtype=np.int16)
                dur = est_dur
                bounds = []
                timing_src = "silent_fallback"
                failed_clauses.append((scene["id"], ci, text, str(e)[:120]))
                _invalidate(wav)
                print(f"  [{scene['id']}] #{ci:02d} TTS失败→静音 {dur:5.2f}s  {text[:38]}")
                print(f"    错误: {str(e)[:120]}")
            n_ok += 1
            chars = finalize_chars(build_chars_from_bounds(text, bounds, dur), dur)
            if timing_src != "silent_fallback":
                print(f"  [{scene['id']}] #{ci:02d} {dur:5.2f}s [{timing_src}]  {text[:38]}")
            sc["clauses"].append({
                "i": ci,
                "text": text,
                "start": round(TITLE_PAD + cursor, 4),
                "end": round(TITLE_PAD + cursor + dur, 4),
                "duration": round(dur, 4),
                "chars": chars,
                "timing_src": timing_src,
            })
            all_pcm.append(data)
            cursor += dur
        scenes_out.append(sc)

    # 前置静音 -> master.wav
    pad = np.zeros(int(SAMPLE_RATE * TITLE_PAD), dtype=np.int16)
    master = np.concatenate([pad] + all_pcm)
    master_path = os.path.join(AUDIO_DIR, "master.wav")
    with wave.open(master_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(master.tobytes())
    shutil.copy(master_path, PUBLIC_AUDIO)

    timeline = {
        "date": narration.get("date", ""),
        "title": narration.get("title", ""),
        "subtitle": narration.get("subtitle", ""),
        "narration": narration,
        "scenes": scenes_out,
        "master_duration": round(len(master) / SAMPLE_RATE, 4),
        "content_duration": round(cursor, 4),
        "master_sha256": sha256_file(master_path),   # P0-4：render 校验音频与时间轴同源
        "master_voice": tts_backend.active_voice(backend),
        "speech_rate": SPEECH_RATE,
        "loudness_rate": LOUDNESS_RATE,
        "title_pad": TITLE_PAD,
        "tts_backend": backend,
        "failed_clauses": [
            {"scene": s, "index": i, "text": t, "error": e}
            for s, i, t, e in failed_clauses
        ],
    }
    with open(args.timeline, "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)

    # --- Whisper 强制对齐（非 edge 后端或 --align whisper 时）---
    use_whisper = (args.align == "whisper") or (
        args.align == "auto" and backend != "edge"
    )
    if use_whisper:
        print(f"\n[align] 用 faster-whisper 做逐词对齐（backend={backend}, align={args.align}）...")
        align_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "align_whisper.py")
        r = subprocess.run(
            [sys.executable, align_script, "--timeline", args.timeline],
            encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            print("[align] Whisper 对齐失败，保留原时间戳（可能漂移）")
        else:
            print("[align] Whisper 对齐完成，timeline 已更新")

    print(f"DONE {n_ok} 句配音 | 内容 {cursor:.1f}s | 整轨 {timeline['master_duration']}s")
    if failed_clauses:
        print(f"⚠️  {len(failed_clauses)} 句 TTS 失败（静音占位），可用 --force 重跑:")
        for s, i, t, e in failed_clauses:
            print(f"    [{s}] #{i:02d} {t[:40]}")
    print(f"master.wav  -> {PUBLIC_AUDIO}")
    print(f"timeline.json -> {args.timeline}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
