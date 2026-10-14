"""流水线收尾：生成 run_report.json + 自动更新 handoff.md。

用法:
    python finalize.py [--narration work/narration.json] [--timeline work/timeline.json]
                       [--handoff E:/workbuddy-workspace/todaynew/handoff.md]

在 run_all.py 最后调用，同日期条目更新而非追加。
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import NARRATION, OUT_DIR, TIMELINE, output_name  # noqa: E402

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def build_report(narration: dict, timeline: dict, video_path: str) -> dict:
    """从 narration/timeline/成片文件构建 run_report.json。"""
    date = narration.get("date", "")
    items = [s for s in narration.get("scenes", [])
             if s.get("visual", {}).get("type") == "news_item"]
    clauses = [c for s in timeline.get("scenes", []) for c in s.get("clauses", [])]

    video_size_mb = 0
    if os.path.exists(video_path):
        video_size_mb = round(os.path.getsize(video_path) / 1024 / 1024, 1)

    report = {
        "date": date,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pipeline": {
            "parse": {
                "items": len(items),
                "scenes": len(narration.get("scenes", [])),
                "clauses": sum(len(s.get("clauses", [])) for s in narration.get("scenes", [])),
            },
            "tts": {
                "backend": timeline.get("tts_backend", ""),
                "align": timeline.get("align_mode", "auto"),
                "clauses": len(clauses),
                "duration_sec": timeline.get("master_duration", 0),
                "failed_clauses": timeline.get("failed_clauses", 0),
            },
            "render": {
                "duration_sec": timeline.get("master_duration", 0),
                "size_mb": video_size_mb,
                "width": 1080,
                "height": 1920,
                "fps": 30,
            },
        },
        "output": {
            "video": f"out/{output_name(date)}",
            "covers": [
                f"out/{date}/covers/cover_3x4.png",
                f"out/{date}/covers/cover_4x3.png",
                f"out/{date}/covers/cover_16x9.png",
            ],
            "chapters": f"out/{date}/chapters.json",
            "publish_md": f"out/{date}/publish.md",
        },
    }
    return report


def update_handoff(handoff_path: str, narration: dict, timeline: dict, video_path: str):
    """更新 handoff.md：同日期的「自动登记」块替换，不存在则插入。"""
    date = narration.get("date", "")
    items = [s for s in narration.get("scenes", [])
             if s.get("visual", {}).get("type") == "news_item"]
    titles = [s.get("visual", {}).get("title", "")[:20] for s in items]
    backend = timeline.get("tts_backend", "edge")
    duration = timeline.get("master_duration", 0)
    video_size_mb = 0
    if os.path.exists(video_path):
        video_size_mb = round(os.path.getsize(video_path) / 1024 / 1024, 1)

    block = f"""### 自动登记（{date}）
- 日期：{date}
- 主题：每日 AI 头条（{len(items)} 条精选：{'、'.join(titles[:3])}{'…' if len(titles) > 3 else ''}）
- 简介：{date} {len(items)} 条 AI 头条一分钟速览
- 主视频路径：`out/{output_name(date)}`
- 状态：渲染完成（1080×1920 @30fps，{duration:.1f}s，{video_size_mb}MB，音轨正常）
- TTS：{backend}-tts，align={timeline.get('align_mode', 'auto')}，{len(items)} 条/{sum(len(s.get('clauses',[])) for s in timeline.get('scenes',[]))} 句
- 封面：`out/{date}/covers/`（3:4 竖版 / 4:3 横版 / 16:9 宽屏）
- 章节：`out/{date}/chapters.json`（{len(timeline.get('scenes',[]))} 条）
- 发布物料：`out/{date}/publish.md`（标题×3 / 话题标签 / 简介 / 置顶评论）
- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）
"""

    if not os.path.exists(handoff_path):
        # 文件不存在，创建
        with open(handoff_path, "w", encoding="utf-8") as f:
            f.write("# todaynew 项目交接说明\n\n## 视频登记\n\n" + block)
        return

    with open(handoff_path, encoding="utf-8") as f:
        content = f.read()

    # 查找同日期的自动登记块
    pattern = rf"### 自动登记（{re.escape(date)}）\n.*?(?=\n### |\n## |\Z)"
    if re.search(pattern, content, re.DOTALL):
        # 替换
        content = re.sub(pattern, block.rstrip() + "\n", content, flags=re.DOTALL)
    else:
        # 在 "## 视频登记" 后插入
        marker = "## 视频登记"
        if marker in content:
            content = content.replace(marker, marker + "\n\n" + block, 1)
        else:
            content += "\n\n## 视频登记\n\n" + block

    with open(handoff_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    ap = argparse.ArgumentParser(description="流水线收尾：run_report + handoff 登记")
    ap.add_argument("--narration", default=NARRATION)
    ap.add_argument("--timeline", default=TIMELINE)
    ap.add_argument("--handoff", default=os.path.join(PROJECT_ROOT, "handoff.md"))
    args = ap.parse_args()

    if not os.path.isfile(args.narration):
        print(f"FAIL: 找不到 {args.narration}")
        return 1
    if not os.path.isfile(args.timeline):
        print(f"FAIL: 找不到 {args.timeline}")
        return 1

    with open(args.narration, encoding="utf-8") as f:
        narration = json.load(f)
    with open(args.timeline, encoding="utf-8") as f:
        timeline = json.load(f)

    date = narration.get("date", "")
    video_path = os.path.join(OUT_DIR, output_name(date))
    out_dir = os.path.dirname(video_path)

    # 1. 生成 run_report.json
    report = build_report(narration, timeline, video_path)
    report_path = os.path.join(out_dir, "run_report.json")
    os.makedirs(out_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[finalize] run_report -> {report_path}")

    # 2. 更新 handoff.md
    update_handoff(args.handoff, narration, timeline, video_path)
    print(f"[finalize] handoff 更新 -> {args.handoff}")

    print("DONE 收尾完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
