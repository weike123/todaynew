"""可插拔 TTS 后端。

- `volc`：火山引擎 seed-tts-2.0 双向流式（首选，真人声，需可用 API Key）
- `edge`：edge-tts（免费兜底，无需 Key，网络可用即可）
- `gptsovits`：本地 GPT-SoVITS v2Pro 零样本克隆（api_v2, 127.0.0.1:9880，main 参考音频）

对外只暴露 synth()/probe()，上层 gen_tts.py 不关心具体后端。
音频统一产出：24kHz / mono / int16 的 wav。
"""
import asyncio
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import SAMPLE_RATE, ffmpeg_path  # noqa: E402

VOLC_VOICE = "zh_female_sophie_uranus_bigtts"
# 默认音色：zh-CN-YunxiNeural（云希，男声，中英混读发音准确；可用环境变量覆盖）
EDGE_VOICE = os.environ.get("TTS_EDGE_VOICE", "zh-CN-YunxiNeural")

# GPT-SoVITS：api_v2 端点 + 音色注册表（voice/cloned_voices.json，default 默认为苏菲）
GSV_API = os.environ.get("GSV_API", "http://127.0.0.1:9880")
GSV_REGISTRY = os.environ.get(
    "GSV_REGISTRY", r"E:\code\GPT-SoVITS\voice\cloned_voices.json"
)
GSV_VOICE = os.environ.get("GSV_VOICE", "")   # 空 = 注册表 default（当前 zh_female_sophie_uranus_bigtts）
GSV_TIMEOUT = int(os.environ.get("GSV_TIMEOUT", "900"))

BACKENDS = ("volc", "edge", "gptsovits")


def active_voice(backend: str) -> str:
    """返回当前后端实际使用的音色标识（供 TTS 缓存指纹绑定，P2-1）。

    音色变化必须使缓存失效：指纹只含「后端名」时，换音色会错误复用旧 wav。
    """
    if backend == "volc":
        return os.environ.get("VOLC_TTS_VOICE", VOLC_VOICE)
    if backend == "edge":
        return EDGE_VOICE
    if backend == "gptsovits":
        try:
            voice, _, _ = _gsv_voice_info()
            return voice
        except (OSError, RuntimeError, ValueError):
            return GSV_VOICE or "gsv-default"
    return backend


def _gsv_voice_info():
    """从音色注册表取 (ref_audio, ref_text)。默认取注册表 default 音色。"""
    import json
    with open(GSV_REGISTRY, "r", encoding="utf-8") as f:
        reg = json.load(f)
    voice = GSV_VOICE or reg.get("default")
    info = reg["voices"].get(voice)
    if not info:
        raise RuntimeError(f"GPT-SoVITS 注册表中无音色 {voice}: {list(reg['voices'])}")
    return voice, info["ref_audio"], info["ref_text"]


# -------------------------------------------------------------------------- volc

def _synth_volc(text, out_wav, speech_rate, loudness_rate, emotion):
    from tts_client import synth_text
    synth_text(
        text, out_wav,
        speech_rate=speech_rate,
        loudness_rate=loudness_rate,
        emotion=emotion,
    )


# -------------------------------------------------------------------------- edge

WORD_BOUNDARY_UNITS = 10_000_000.0   # edge-tts 的 offset/duration 以 100ns 为单位

# 单句合成超时（秒）。edge-tts 的 websocket 在某些情况下会静默挂住不返回，
# 无超时会让整条流水线卡死；超时后抛错交给 gen_tts.py 重试逻辑处理。
EDGE_TIMEOUT = int(os.environ.get("TTS_EDGE_TIMEOUT", "60"))


def _synth_edge(text, out_wav, speech_rate, loudness_rate, emotion=None):
    """edge-tts 合成，同时捕获 WordBoundary 用于生成准确的 KTV 字幕时间戳。

    返回：词边界列表，每个元素包含 {offset, duration, text, offset_sec, duration_sec}。
    时间单位：offset/duration 为原始 100ns 整数，offset_sec/duration_sec 为秒。
    """
    import edge_tts

    # edge-tts 的 rate/volume 是百分比字符串，正好映射「语速 +30% / 音量 +50%」
    rate = f"+{speech_rate}%" if speech_rate >= 0 else f"{speech_rate}%"
    volume = f"+{loudness_rate}%" if loudness_rate >= 0 else f"{loudness_rate}%"

    async def _stream():
        comm = edge_tts.Communicate(
            text, EDGE_VOICE, rate=rate, volume=volume, boundary="WordBoundary"
        )
        audio = bytearray()
        bounds = []
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                bounds.append({
                    "offset": chunk["offset"],
                    "duration": chunk["duration"],
                    "text": chunk["text"],
                    "offset_sec": chunk["offset"] / WORD_BOUNDARY_UNITS,
                    "duration_sec": chunk["duration"] / WORD_BOUNDARY_UNITS,
                })
        return bytes(audio), bounds

    try:
        mp3_bytes, word_bounds = asyncio.run(
            asyncio.wait_for(_stream(), timeout=EDGE_TIMEOUT)
        )
    except asyncio.TimeoutError:
        raise RuntimeError(f"edge-tts 合成超时（>{EDGE_TIMEOUT}s）: {text[:20]}...")

    if not mp3_bytes or len(mp3_bytes) < 256:
        raise RuntimeError("edge-tts 未产出音频")

    # 中转 mp3 写到系统临时目录（不删工作区文件，也避免触发批量删除防护）
    fd, mp3 = tempfile.mkstemp(suffix=".mp3")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(mp3_bytes)

        # mp3 -> 24kHz mono wav（与火山后端保持一致的采样率）
        cmd = [
            ffmpeg_path(), "-y", "-hide_banner", "-loglevel", "error",
            "-i", mp3, "-ar", str(SAMPLE_RATE), "-ac", "1", "-f", "wav", out_wav,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(out_wav):
            raise RuntimeError(f"ffmpeg 转码失败: {r.stderr[-300:]}")
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
    return word_bounds


# --------------------------------------------------------------------- gptsovits

def _synth_gptsovits(text, out_wav, speech_rate, loudness_rate, emotion=None):
    """本地 GPT-SoVITS api_v2 零样本克隆（音色取注册表，默认苏菲）。

    语速映射：speech_rate 百分比 -> speed_factor（+30% => 1.3）；
    loudness_rate 后端不支持，由 gen_tts.py 的响度归一统一兜底
    （克隆输出固有偏轻 8~12dB，归一化正好补齐）。
    参考音频产出 32kHz，ffmpeg 转码到统一的 24kHz mono wav。
    GPT-SoVITS 无词边界信息，恒返回 []（KTV 字幕退回均分时间轴）。
    注意：本机全局代理会劫持 127.0.0.1，必须 trust_env=False。
    """
    import requests

    voice, ref_audio, ref_text = _gsv_voice_info()
    sess = requests.Session()
    sess.trust_env = False                      # 绕开本机代理（否则 127.0.0.1 被劫持成 502）
    r = sess.post(f"{GSV_API}/tts", json={
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": ref_audio,
        "prompt_text": ref_text,
        "prompt_lang": "zh",
        "text_split_method": "cut5",
        "batch_size": 1,
        "speed_factor": round(1.0 + speech_rate / 100.0, 3),
        "top_k": 15, "top_p": 1.0, "temperature": 1.0,
        "repetition_penalty": 1.35,
        "media_type": "wav",
        "streaming_mode": False,
        "seed": -1,
    }, timeout=GSV_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(
            f"GPT-SoVITS /tts HTTP {r.status_code} (voice={voice}): {r.text[:300]}"
        )
    if len(r.content) < 1024:
        raise RuntimeError("GPT-SoVITS 未产出音频")

    fd, src = tempfile.mkstemp(suffix=".wav")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(r.content)
        cmd = [
            ffmpeg_path(), "-y", "-hide_banner", "-loglevel", "error",
            "-i", src, "-ar", str(SAMPLE_RATE), "-ac", "1", "-f", "wav", out_wav,
        ]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0 or not os.path.exists(out_wav):
            raise RuntimeError(f"ffmpeg 转码失败: {p.stderr[-300:]}")
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
    return []


# -------------------------------------------------------------------------- 统一入口

def synth(text, out_wav, backend="volc", speech_rate=30, loudness_rate=50,
          emotion="neutral", return_timing=False):
    """合成单句到 out_wav。backend: volc | edge | gptsovits

    return_timing=True 时返回词边界列表（edge 后端才有；volc/gptsovits 恒为 []），
    供 gen_tts.py 生成与真实发音对齐的逐字字幕时间戳。
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_wav)) or ".", exist_ok=True)
    if backend == "volc":
        _synth_volc(text, out_wav, speech_rate, loudness_rate, emotion)
        return [] if return_timing else None
    elif backend == "edge":
        bounds = _synth_edge(text, out_wav, speech_rate, loudness_rate)
        return bounds if return_timing else None
    elif backend == "gptsovits":
        _synth_gptsovits(text, out_wav, speech_rate, loudness_rate, emotion)
        return [] if return_timing else None
    else:
        raise ValueError(f"未知 TTS 后端: {backend}")


def probe(backend="volc", timeout_probe_text="测试。"):
    """探测后端是否可用，返回 (ok, msg)。"""
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), f"_tts_probe_{backend}.wav")
    try:
        synth(timeout_probe_text, tmp, backend=backend,
              speech_rate=0, loudness_rate=0)
        ok = os.path.exists(tmp) and os.path.getsize(tmp) > 1024
        return ok, "ok" if ok else "输出为空"
    except Exception as e:
        return False, str(e)[:200]
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def choose_backend(preferred="auto"):
    """选择后端。auto = 先试火山，不可用则降级 edge。"""
    if preferred in BACKENDS:
        ok, msg = probe(preferred)
        if not ok:
            raise RuntimeError(f"指定后端 {preferred} 不可用: {msg}")
        print(f"[tts] 使用后端: {preferred}")
        return preferred

    for b in BACKENDS:
        ok, msg = probe(b)
        if ok:
            print(f"[tts] 自动选择后端: {b}")
            return b
        print(f"[tts] 后端 {b} 不可用，跳过（{msg[:90]}）")
    raise RuntimeError("所有 TTS 后端都不可用：请检查火山 API Key 或网络连通性")


if __name__ == "__main__":
    b = sys.argv[1] if len(sys.argv) > 1 else "auto"
    try:
        chosen = choose_backend(b)
        print("CHOSEN:", chosen)
    except Exception as e:
        print("FAIL:", e)
        sys.exit(1)
