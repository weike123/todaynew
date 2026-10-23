"""生成一份极小的 timeline.json + narration.json + 静音 master.wav，
用于快速验证 Remotion 工程能否编译/渲染，以及收尾环节能否跑通。

    python smoke_fixture.py            # 生成 6s 冒烟数据
    python smoke_fixture.py --restore  # 无操作（保留真实数据不被覆盖）

设计约束（2026-10-23 修复）：
冒烟数据必须能通过 validate_output.py 的全部 ERROR 级校验，否则
`run_all.py --smoke` 会在 validate 阶段被拦下，反而测不到渲染链路。
因此本 fixture 产出：
  - narration 必填字段齐备（date / scenes / total）
  - 每条新闻自带一张**真实可解码**的 PNG 配图（现场用 PIL 生成，
    不依赖图库 Key、不依赖网络），来源标记为 fixture（非海报兜底）
  - clauses 以完整标点收尾，narration 与 timeline 内嵌 narration 完全一致
  - 场景时间轴连续、逐字时间戳相对句首且单调
"""
import json
import os
import shutil
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (AUDIO_DIR, IMAGES_DIR, NARRATION, PUBLIC_AUDIO,  # noqa: E402
                    SAMPLE_RATE, TIMELINE, WORK_DIR, ensure_dirs)

DUR = 6.0
SMOKE_DATE = "2026-09-06"


def _make_fixture_image(path: str) -> tuple:
    """生成一张真实可解码的 PNG 配图（渐变 + 色块，非纯色）。

    返回 (文件名, [宽, 高])。
    用真实图片而非纯色块，避免触发 validate_output 的图片解码检查失败。
    """
    from PIL import Image, ImageDraw
    os.makedirs(os.path.dirname(path), exist_ok=True)
    w, h = 640, 360
    img = Image.new("RGB", (w, h), (32, 48, 84))
    dr = ImageDraw.Draw(img)
    # 纵向渐变
    for y in range(h):
        t = y / h
        dr.line([(0, y), (w, y)],
                fill=(int(32 + 40 * t), int(48 + 60 * t), int(84 + 80 * t)))
    # 几个色块，制造纹理与结构（确保不是纯色）
    for x0, y0, x1, y1, c in [
        (40, 60, 200, 240, (79, 140, 255)),
        (220, 120, 380, 300, (34, 211, 238)),
        (400, 40, 580, 180, (255, 214, 10)),
    ]:
        dr.rectangle([x0, y0, x1, y1], fill=c)
    img.save(path, "PNG")
    return os.path.basename(path), [w, h]


def build():
    ensure_dirs()
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # ---- 真实配图：现场生成，不依赖网络与图库 Key ----
    img_file, img_dims = _make_fixture_image(os.path.join(IMAGES_DIR, "fixture_smoke.png"))
    img_ref = f"images/{img_file}"

    clauses = [
        "冒烟测试第一句，用于验证字幕渲染。",
        "冒烟测试第二句，检查卡拉OK高亮。",
        "冒烟测试第三句，验证时间轴连续性。",
    ]
    specs = [
        ("s0_intro", {"type": "news_hook", "date": SMOKE_DATE, "weekday": "周日",
                      "total": 1, "sections": ["全球大模型", "AI Coding", "开源项目"]}),
        ("s1_item", {"type": "news_item", "index": 1, "section": "全球大模型",
                     "title": "冒烟测试标题：验证 9:16 竖屏渲染链路是否通畅",
                     "tags": ["测试", "冒烟"], "source": "smoke",
                     "images": [img_ref], "image_sizes": [img_dims],
                     "image_source": "fixture"}),
        ("s2_outro", {"type": "news_outro", "date": SMOKE_DATE, "total": 1}),
    ]

    scenes, cursor = [], 0.0
    for i, (sid, visual) in enumerate(specs):
        text = clauses[i]
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

    # ---- narration：clauses 为字符串列表（与 parse_news 真实产出一致）----
    narration = {
        "date": SMOKE_DATE,
        "title": "每日 AI 头条",
        "subtitle": "smoke",
        "weekday": "周日",
        "total": 1,
        "sections": ["全球大模型", "AI Coding", "开源项目"],
        "scenes": [
            {
                "id": s["id"],
                "visual": dict(specs[i][1]),
                "clauses": [s["clauses"][0]["text"]],
            }
            for i, s in enumerate(scenes)
        ],
    }

    tl = {
        "date": SMOKE_DATE,
        "title": "每日 AI 头条",
        "subtitle": "smoke",
        "narration": narration,
        "scenes": scenes,
        "master_duration": round(cursor, 4),
        "content_duration": round(cursor, 4),
        "speech_rate": 30, "loudness_rate": 50, "title_pad": 0.1,
        "tts_backend": "smoke",
        "align_mode": "smoke",
        "failed_clauses": [],
    }

    os.makedirs(WORK_DIR, exist_ok=True)
    with open(TIMELINE, "w", encoding="utf-8") as f:
        json.dump(tl, f, ensure_ascii=False, indent=2)
    with open(NARRATION, "w", encoding="utf-8") as f:
        json.dump(narration, f, ensure_ascii=False, indent=2)

    pcm = np.zeros(int(SAMPLE_RATE * cursor), dtype=np.int16)
    path = os.path.join(AUDIO_DIR, "master.wav")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    os.makedirs(os.path.dirname(PUBLIC_AUDIO), exist_ok=True)
    shutil.copy(path, PUBLIC_AUDIO)
    print(f"SMOKE fixture ready: {cursor:.1f}s -> {TIMELINE}")
    print(f"  配图: {img_ref} {img_dims[0]}x{img_dims[1]}")


if __name__ == "__main__":
    build()
