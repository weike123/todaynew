"""流水线收尾：生成 run_report.json + 自动更新 handoff.md。

用法:
    python finalize.py [--narration work/narration.json] [--timeline work/timeline.json]
                       [--video out/<date>/每日ai热门新闻-<date>.mp4]
                       [--handoff <项目根>/handoff.md]

在 run_all.py 最后调用，同日期条目更新而非追加。

run_report.json 状态语义（2026-10-14 T1）：
- READY     完整物料齐全且最终成片实测通过，可交外部发布
- GENERATED 文件已生成但未完成发布前验收（缺物料）
- BLOCKED   失败阶段与恢复方式已记录，不得发布

外部发布技能写回 run_report 的 publish 字段与 handoff 的 publish 区，
finalize 重写时原样保留，不覆盖既有平台回执。
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    FPS, HEIGHT, NARRATION, OUT_DIR, PROJECT_ROOT, TIMELINE, WIDTH, output_name,
    probe_video, sha256_file,
)

FINALIZE_BEGIN = "<!-- finalize:begin -->"
FINALIZE_END = "<!-- finalize:end -->"
PUBLISH_BEGIN = "<!-- publish:begin -->"
PUBLISH_END = "<!-- publish:end -->"

# READY 门要求的物料（相对成片目录）
REQUIRED_ARTIFACTS = ("publish.md", "chapters.json")
REQUIRED_COVERS = ("cover_3x4.png", "cover_4x3.png", "cover_16x9.png")


def _fmt_dur(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    return f"{m:02d}:{s:02d}"


def build_report(narration: dict, timeline: dict, video_path: str,
                 out_dir: str = "") -> dict:
    """从 narration/timeline/最终成片构建 run_report.json（全部实测）。"""
    date = narration.get("date", "")
    items = [s for s in narration.get("scenes", [])
             if s.get("visual", {}).get("type") == "news_item"]
    clauses = [c for s in timeline.get("scenes", []) for c in s.get("clauses", [])]

    video_path = os.path.abspath(video_path)
    probe = probe_video(video_path)
    video_size_mb = round(os.path.getsize(video_path) / 1024 / 1024, 1) \
        if os.path.isfile(video_path) else 0

    out_dir = out_dir or os.path.dirname(video_path)
    covers_dir = os.path.join(out_dir, "covers")
    covers = [os.path.join(covers_dir, c) for c in REQUIRED_COVERS]

    # 混音状态来自 render.py 的 render_state.json；缺失记为 unknown（未测）
    mix_status = "unknown"
    loudness = {}
    rs_path = os.path.join(out_dir, "render_state.json")
    if os.path.isfile(rs_path):
        try:
            with open(rs_path, encoding="utf-8") as f:
                rs = json.load(f)
            am = rs.get("audio_mix", {})
            mix_status = f"{am.get('mode', '?')}:{'ok' if am.get('ok') else 'FAILED'}"
            ld = rs.get("loudness") or {}
            if ld.get("integrated_lufs") is not None:
                loudness = ld
        except (OSError, json.JSONDecodeError):
            mix_status = "unreadable"

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
                "failed_clauses": timeline.get("failed_clauses", []),
            },
            "render": {
                "duration_sec": round(probe["duration"], 2),
                "size_mb": video_size_mb,
                "width": probe["width"],
                "height": probe["height"],
                "fps": probe["fps"],
            },
        },
        "video": {
            "path": video_path,
            "sha256": sha256_file(video_path),
            "duration_sec": round(probe["duration"], 2),
            "width": probe["width"],
            "height": probe["height"],
            "fps": probe["fps"],
            "has_audio": probe["has_audio"],
            "size_mb": video_size_mb,
        },
        "quality": {
            "tts_failed": list(timeline.get("failed_clauses", [])),
            "images_missing": [],
            "images_reviewed": False,
            "audio_mix_status": mix_status,
            "integrated_lufs": loudness.get("integrated_lufs"),
            "true_peak_dbtp": loudness.get("true_peak_dbtp"),
            "tail_frame_checked": False,
        },
        "artifacts": {
            "publish_md": os.path.join(out_dir, "publish.md"),
            "chapters": os.path.join(out_dir, "chapters.json"),
            "covers": covers,
        },
        "publish": {},
    }
    return report


def evaluate_status(report: dict) -> tuple:
    """根据报告内容判定 READY / GENERATED / BLOCKED，返回 (status, reasons)。"""
    reasons = []
    v = report["video"]
    if not os.path.isfile(v["path"]):
        return "BLOCKED", ["最终成片文件不存在"]
    if not v["sha256"]:
        return "BLOCKED", ["最终成片无法计算哈希"]
    if not v["has_audio"]:
        reasons.append("成片无音轨")
    if (v["width"], v["height"]) != (WIDTH, HEIGHT):
        reasons.append(f"分辨率异常 {v['width']}x{v['height']}")
    if not v["fps"]:
        reasons.append("无法解析帧率")
    if v["duration_sec"] <= 0:
        reasons.append("无法解析时长")
    for name, path in (("publish.md", report["artifacts"]["publish_md"]),
                       ("chapters.json", report["artifacts"]["chapters"])):
        if not os.path.isfile(path):
            reasons.append(f"缺少物料 {name}")
    for c in report["artifacts"]["covers"]:
        if not os.path.isfile(c):
            reasons.append(f"缺少封面 {os.path.basename(c)}")
    if reasons:
        return "GENERATED", reasons
    return "READY", []


def merge_existing_publish(report: dict, report_path: str) -> dict:
    """保留既有 run_report 中外部发布写回的 publish 回执。"""
    if not os.path.isfile(report_path):
        return report
    try:
        with open(report_path, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, json.JSONDecodeError):
        return report
    if isinstance(old.get("publish"), dict) and old["publish"]:
        report["publish"] = old["publish"]
    return report


def _rel_to_root(path: str) -> str:
    """相对项目根的路径。

    handoff.md 是入库文档，不写本机绝对路径（否则每次跑流水线都会把
    本机目录结构泄漏进 git 历史）。跨盘符等异常情况保持原样。
    """
    try:
        return os.path.relpath(os.path.abspath(path), PROJECT_ROOT)
    except ValueError:
        return path


def _handoff_generation_block(narration: dict, timeline: dict, video_path: str,
                              report: dict) -> str:
    date = narration.get("date", "")
    items = [s for s in narration.get("scenes", [])
             if s.get("visual", {}).get("type") == "news_item"]
    titles = [s.get("visual", {}).get("title", "")[:20] for s in items]
    backend = timeline.get("tts_backend", "edge")
    v = report["video"]
    status = report.get("status", "")
    rel_video = _rel_to_root(video_path)
    rel_dir = os.path.dirname(rel_video)
    lines = [
        f"### 自动登记（{date}）",
        FINALIZE_BEGIN,
        f"- 日期：{date}",
        f"- 主题：每日 AI 头条（{len(items)} 条精选：{'、'.join(titles[:3])}"
        f"{'…' if len(titles) > 3 else ''}）",
        f"- 简介：{date} {len(items)} 条 AI 头条一分钟速览",
        f"- 主视频路径：`{rel_video}`",
        f"- 状态：{status}（{v['width']}×{v['height']} @{v['fps']}fps，"
        f"{v['duration_sec']:.1f}s，{v['size_mb']}MB，"
        f"音轨{'正常' if v['has_audio'] else '缺失'}，sha256 {v['sha256'][:12]}…）",
        f"- TTS：{backend}-tts，align={timeline.get('align_mode', 'auto')}，"
        f"{len(items)} 条/{sum(len(s.get('clauses', [])) for s in timeline.get('scenes', []))} 句",
        f"- 封面：`{os.path.join(rel_dir, 'covers')}/`"
        f"（3:4 竖版 / 4:3 横版 / 16:9 宽屏；发布 JPG 由 video-upload 重绘）",
        f"- 章节：`{os.path.join(rel_dir, 'chapters.json')}`"
        f"（{len(timeline.get('scenes', []))} 条）",
        f"- 发布物料：`{os.path.join(rel_dir, 'publish.md')}`",
        f"- 目标发布平台：抖音 / B站 / 视频号（署名翻奇兽AI）",
        FINALIZE_END,
    ]
    if not report.get("_had_publish_region"):
        lines += [PUBLISH_BEGIN, PUBLISH_END]
    return "\n".join(lines)


def update_handoff(handoff_path: str, narration: dict, timeline: dict,
                   video_path: str, report: dict):
    """更新 handoff.md：只替换 finalize 区，保留 publish 区（平台回执）。"""
    date = narration.get("date", "")
    block = _handoff_generation_block(narration, timeline, video_path, report)

    if not os.path.exists(handoff_path):
        with open(handoff_path, "w", encoding="utf-8") as f:
            f.write("# todaynew 项目交接说明\n\n## 视频登记\n\n" + block + "\n")
        return

    with open(handoff_path, encoding="utf-8") as f:
        content = f.read()

    had_publish_region = (PUBLISH_BEGIN in content and PUBLISH_END in content)
    report["_had_publish_region"] = had_publish_region
    block = _handoff_generation_block(narration, timeline, video_path, report)
    report.pop("_had_publish_region", None)

    # 1) 已有同日自动登记块：只换 finalize 区（无区标志的旧块整块替换并补 publish 区）
    pattern = rf"### 自动登记（{re.escape(date)}）\n.*?(?=\n### |\n## |\Z)"
    if re.search(pattern, content, re.DOTALL):
        if FINALIZE_BEGIN in content:
            # 精细替换：仅 finalize 区
            fin_pattern = (rf"{re.escape(FINALIZE_BEGIN)}.*?{re.escape(FINALIZE_END)}")
            new_fin = FINALIZE_BEGIN + block.split(FINALIZE_BEGIN, 1)[1].split(FINALIZE_END, 1)[0] + FINALIZE_END
            content = re.sub(fin_pattern, lambda _: new_fin, content, count=1, flags=re.DOTALL)
            if not had_publish_region and PUBLISH_BEGIN not in content:
                content = content.replace(FINALIZE_END, FINALIZE_END + "\n" + PUBLISH_BEGIN + "\n" + PUBLISH_END, 1)
        else:
            content = re.sub(pattern, lambda _: block.rstrip() + "\n", content,
                             count=1, flags=re.DOTALL)
    else:
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
    ap.add_argument("--video", default="",
                    help="最终成片路径（默认 out/<date>/每日ai热门新闻-<date>.mp4）")
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
    video_path = os.path.abspath(args.video) if args.video \
        else os.path.join(OUT_DIR, output_name(date))
    out_dir = os.path.dirname(video_path)

    # 1. 生成 run_report.json（实测最终文件）
    report = build_report(narration, timeline, video_path, out_dir=out_dir)
    report_path = os.path.join(out_dir, "run_report.json")
    os.makedirs(out_dir, exist_ok=True)
    report = merge_existing_publish(report, report_path)

    status, reasons = evaluate_status(report)
    report["status"] = status
    if status != "READY":
        report["blocked_reason"] = reasons

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[finalize] run_report -> {report_path} (status={status})")
    if reasons:
        print(f"[finalize] 未达 READY：{'；'.join(reasons)}")

    # 2. 更新 handoff.md（保留平台回执区）
    update_handoff(args.handoff, narration, timeline, video_path, report)
    print(f"[finalize] handoff 更新 -> {args.handoff}")

    if status == "BLOCKED":
        print("FAIL: 最终成片缺失或不可测，已记录 BLOCKED")
        return 1
    print("DONE 收尾完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
