"""生成一份极小的 timeline.json + 静音 master.wav，用于快速验证 Remotion 工程能否编译/渲染。

    python smoke_fixture.py            # 生成 6s 冒烟数据
    python smoke_fixture.py --restore  # 无操作（保留真实数据不被覆盖）
"""
import json
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import AUDIO_DIR, PUBLIC_AUDIO, SAMPLE_RATE, TIMELINE, WORK_DIR, ensure_dirs  # noqa: E402

DUR = 6.0


def build():
    ensure_dirs()
    clauses = [
        "冒烟测试第一句，用于验证字幕渲染。",
        "冒烟测试第二句，检查卡拉OK高亮。",
    ]
    scenes, cursor = [], 0.0
    specs = [
        ("s0_intro", {"type": "news_hook", "date": "2026-09-06", "weekday": "周日",
                      "total": 1, "sections": ["全球大模型", "AI Coding", "开源项目"]}),
        ("s1_item", {"type": "news_item", "index": 1, "section": "全球大模型",
                     "title": "冒烟测试标题：验证 9:16 竖屏渲染链路是否通畅",
                     "tags": ["测试", "冒烟"], "source": "smoke"}),
        ("s2_outro", {"type": "news_outro", "date": "2026-09-06", "total": 1}),
    ]
    for i, (sid, visual) in enumerate(specs):
        text = clauses[i] if i < len(clauses) else "冒烟测试。默认句子。"
        dur = DUR / len(specs)
        chars = [{"ch": c, "t": round(k * dur / max(1, len(text)), 4)}
                 for k, c in enumerate(text)]
        scenes.append({
            "id": sid,
            "clauses": [{"i": 0, "text": text, "start": round(cursor, 4),
                         "end": round(cursor + dur, 4),
                         "duration": round(dur, 4), "chars": chars}],
        })
        cursor += dur

    tl = {
        "date": "2026-09-06",
        "title": "每日 AI 头条",
        "subtitle": "smoke",
        "narration": {
            "date": "2026-09-06", "weekday": "周日", "title": "每日 AI 头条",
            "subtitle": "smoke", "total": 1,
            "sections": ["全球大模型", "AI Coding", "开源项目"],
            "scenes": [{"id": s["id"], "visual": v} for s, (_, v) in zip(scenes, specs)],
        },
        "scenes": scenes,
        "master_duration": round(cursor, 4),
        "content_duration": round(cursor, 4),
        "speech_rate": 30, "loudness_rate": 50, "title_pad": 0.1,
        "tts_backend": "smoke",
    }
    with open(TIMELINE, "w", encoding="utf-8") as f:
        json.dump(tl, f, ensure_ascii=False, indent=2)

    pcm = np.zeros(int(SAMPLE_RATE * cursor), dtype=np.int16)
    path = os.path.join(AUDIO_DIR, "master.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    os.makedirs(os.path.dirname(PUBLIC_AUDIO), exist_ok=True)
    import shutil
    shutil.copy(path, PUBLIC_AUDIO)
    print(f"SMOKE fixture ready: {cursor:.1f}s -> {TIMELINE}")


if __name__ == "__main__":
    build()
