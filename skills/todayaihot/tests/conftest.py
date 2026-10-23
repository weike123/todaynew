"""todayaihot 测试公共 helper：fixture 视频生成与临时产物。"""
import json
import os
import shutil
import subprocess
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(os.path.dirname(TESTS_DIR), "scripts")
sys.path.insert(0, SCRIPTS_DIR)

# 已知完整 ffmpeg 候选（Remotion 自带精简构建无 lavfi，不能用于生成 fixture）
FFMPEG_CANDIDATES = [
    os.environ.get("TODAYAIHOT_FFMPEG", ""),
    r"D:/download/ffmpeg_v7.1.1_essentials_build_9663.com/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe",
]


def full_ffmpeg():
    """返回支持 lavfi 的完整 ffmpeg 路径；找不到返回 None。"""
    from shutil import which
    cands = list(FFMPEG_CANDIDATES) + [which("ffmpeg") or ""]
    for c in cands:
        if not c or not os.path.exists(c):
            continue
        try:
            r = subprocess.run(
                [c, "-hide_banner", "-loglevel", "error",
                 "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "0.1",
                 "-f", "null", "-"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0:
                return c
        except (OSError, subprocess.SubprocessError):
            continue
    return None


@pytest.fixture(scope="session")
def ffmpeg():
    ff = full_ffmpeg()
    if ff is None:
        pytest.skip("未找到支持 lavfi 的完整 ffmpeg，跳过需要真实视频的用例")
    return ff


def make_video(ffmpeg, path, width=1080, height=1920, duration=3.0, fps=30):
    """生成一段带音轨的测试视频（黑场 + 静音）。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:d={duration}:r={fps}",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"生成测试视频失败: {r.stderr[-500:]}"
    assert os.path.exists(path)
    return path


def make_narration(date="2026-10-14", n_items=3):
    """narration.json 中 clauses 为纯字符串（与 parse_news 真实产出一致）。"""
    scenes = [{
        "id": "s0_hook",
        "visual": {"type": "news_hook", "title": "今日 AI 速览"},
        "clauses": ["今天 AI 圈有大事。"],
    }]
    for i in range(n_items):
        scenes.append({
            "id": f"s{i+1}_item",
            "visual": {"type": "news_item", "title": f"第{i+1}条新闻标题",
                       "source": "测试来源", "link": "https://example.com"},
            "clauses": [f"第{i+1}条完整口播句。"],
        })
    scenes.append({
        "id": "s_out",
        "visual": {"type": "news_outro", "title": "结尾"},
        "clauses": ["明天见。"],
    })
    return {"date": date, "title": "每日 AI 头条", "total": n_items, "scenes": scenes}


def make_timeline(date="2026-10-14", master_duration=99.0):
    """master_duration 故意设成与真实视频不同的值，抓'拿 master 充视频时长'的旧 bug。"""
    scenes = [{
        "id": "s0_hook",
        "visual": {"type": "news_hook"},
        "clauses": [{"text": "今天 AI 圈有大事。", "start": 0.1, "end": 2.0,
                     "chars": [{"ch": "今", "t": 0.0}, {"ch": "。", "t": 1.5}]}],
    }]
    for i in range(3):
        start = 2.0 + 2 * i
        scenes.append({
            "id": f"s{i+1}_item",
            "visual": {"type": "news_item"},
            "clauses": [{"text": f"第{i+1}条完整口播句。", "start": start, "end": start + 2.0,
                         "chars": [{"ch": "第", "t": 0.0}, {"ch": "。", "t": 1.5}]}],
        })
    return {
        "date": date,
        "master_duration": master_duration,
        "content_duration": master_duration - 0.1,
        "tts_backend": "edge",
        "align_mode": "edge",
        "failed_clauses": [],
        "scenes": scenes,
    }


def write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path


def write_real_png(path, size=(64, 48), color=(90, 120, 200)):
    """生成一张真实可解码的 PNG（PIL），供配图校验使用。"""
    from PIL import Image
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Image.new("RGB", size, color).save(path, "PNG")
    return path


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256_of(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
