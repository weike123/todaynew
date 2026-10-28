"""流水线收尾：生成 run_report.json + 自动更新 handoff.md。

用法:
    python finalize.py [--narration work/narration.json] [--timeline work/timeline.json]
                       [--video out/<date>/每日ai热门新闻-<date>.mp4]
                       [--handoff <项目根>/handoff.md]

在 run_all.py 最后调用，同日期条目更新而非追加。

run_report.json 状态语义（2026-10-28 P0-1 收紧）：
- READY     物料齐全、最终成片实测通过，且人工审图/片尾检查已有记录（绑定同一 SHA256）
- GENERATED 文件已生成，但必有质量检查未完成（未审图/未查片尾/响度未测或超标）
- BLOCKED   生成失败（TTS 失败句）、混音失败或成片不可测，不得发布

质量字段约定：
- build_report 每次重建 quality（images_reviewed / tail_frame_checked 默认 False）；
  人工审阅后直接改 run_report.json 对应字段，再重跑 finalize 即可升级 READY。
- 审阅记录与 quality.video_sha256 绑定：重渲染产生新哈希 → 旧审阅作废，必须重审。
- 未测字段保持 False/None，绝不写成 0 或成功。

外部发布技能写回 run_report 的 publish 字段与 handoff 的 publish 区，
finalize 重写时：同一视频 SHA256 的回执原样保留；哈希不一致（新版本）不继承
旧回执，避免旧版成功状态伪装成新版已发布。
"""
import argparse
import json
import os
import re
import shutil
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

# 响度门（项目内部目标，非平台强制标准）：-14±1 LUFS、真峰值 ≤ -1 dBTP
LOUDNESS_TARGET_LUFS = -14.0
LOUDNESS_TOLERANCE = 1.0
TRUE_PEAK_MAX = -1.0

HANDOFF_MAX_BYTES = 24 * 1024      # handoff.md 体积上限，超限归档历史日期块


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

    # 混音状态与流级实测来自 render.py 的 render_state.json；
    # 缺失记为 unknown/None（未测），绝不写成成功（P0-1/P0-2）
    mix_status = "unknown"
    mix_ok = None
    loudness = {}
    streams = None
    rs_path = os.path.join(out_dir, "render_state.json")
    if os.path.isfile(rs_path):
        try:
            with open(rs_path, encoding="utf-8") as f:
                rs = json.load(f)
            am = rs.get("audio_mix", {})
            mix_ok = am.get("ok")
            mix_status = f"{am.get('mode', '?')}:{'ok' if am.get('ok') else 'FAILED'}"
            ld = rs.get("loudness") or {}
            if ld.get("integrated_lufs") is not None:
                loudness = ld
            streams = rs.get("streams")
        except (OSError, json.JSONDecodeError):
            mix_status = "unreadable"

    video_sha = sha256_file(video_path)
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
            "sha256": video_sha,
            "duration_sec": round(probe["duration"], 2),
            "width": probe["width"],
            "height": probe["height"],
            "fps": probe["fps"],
            "has_audio": probe["has_audio"],
            "size_mb": video_size_mb,
            "streams": streams,      # 音/视频流级时长与帧数；未测为 None（P0-2）
        },
        "quality": {
            "video_sha256": video_sha,   # 审阅记录绑定该哈希；重渲染即失效
            "tts_failed": list(timeline.get("failed_clauses", [])),
            "images_missing": [],
            "images_reviewed": False,    # 人工审图后改为 true（审阅对象 = 本哈希）
            "reviewed_by": "",
            "audio_mix_status": mix_status,
            "audio_mix_ok": mix_ok,      # None=未测；False=混音失败（BLOCKED）
            "integrated_lufs": loudness.get("integrated_lufs"),
            "true_peak_dbtp": loudness.get("true_peak_dbtp"),
            "tail_frame_checked": False, # 人工检查末帧后改为 true
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
    """根据报告内容判定 READY / GENERATED / BLOCKED，返回 (status, reasons)。

    P0-1 质量门：
    - BLOCKED：成片不可测、TTS 失败句存在、混音明确失败；
    - GENERATED：成片可用但必选质量检查未完成（未审图/未查片尾/响度未测或超标）
      或缺物料；
    - READY：物料齐全 + 全部质量检查有合格记录。
    """
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

    q = report.get("quality", {})
    if q.get("tts_failed"):
        return "BLOCKED", [f"存在 {len(q['tts_failed'])} 句 TTS 失败（静音占位），不得发布"]
    if q.get("audio_mix_ok") is False:
        return "BLOCKED", [f"混音失败（{q.get('audio_mix_status', 'unknown')}），候选片不作为成片发布"]
    if q.get("audio_mix_ok") is None:
        reasons.append("混音状态未测（render_state 缺失）")
    if not q.get("images_reviewed"):
        reasons.append("配图未人工审阅（images_reviewed=false）")
    if not q.get("tail_frame_checked"):
        reasons.append("片尾末帧未检查（tail_frame_checked=false）")

    lufs = q.get("integrated_lufs")
    tp = q.get("true_peak_dbtp")
    if lufs is None or tp is None:
        reasons.append("成片响度未实测")
    else:
        if abs(lufs - LOUDNESS_TARGET_LUFS) > LOUDNESS_TOLERANCE:
            reasons.append(f"综合响度 {lufs} LUFS 偏离 {LOUDNESS_TARGET_LUFS:g}±{LOUDNESS_TOLERANCE:g} 目标")
        if tp > TRUE_PEAK_MAX:
            reasons.append(f"真峰值 {tp} dBTP 超过 {TRUE_PEAK_MAX:g} 目标")

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


def _load_old_report(report_path: str) -> dict:
    if not os.path.isfile(report_path):
        return {}
    try:
        with open(report_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def merge_existing_quality(report: dict, report_path: str) -> dict:
    """继承既有 run_report 中的人工审阅字段（P0-1）。

    仅当旧报告的 quality.video_sha256 与当前成片哈希一致时才继承
    images_reviewed / reviewed_by / tail_frame_checked：重渲染产生新哈希，
    旧审阅自动作废，必须重审。哈希不一致或旧报告无该字段则不继承。
    """
    old = _load_old_report(report_path)
    old_q = old.get("quality") or {}
    if old_q.get("video_sha256") and old_q["video_sha256"] == report["quality"]["video_sha256"]:
        for key in ("images_reviewed", "reviewed_by", "tail_frame_checked"):
            if key in old_q:
                report["quality"][key] = old_q[key]
    return report


def merge_existing_publish(report: dict, report_path: str) -> dict:
    """继承既有 run_report 中外部发布写回的平台回执（P0-3 哈希绑定）。

    回执只属于它发布时的那个视频版本：
    - 旧报告 video.sha256 与当前一致 → 回执原样继承；
    - 不一致（成片已重渲染为新版本）→ 不继承，避免旧版成功状态伪装成新版已发布；
    - 旧报告无哈希（历史遗留）→ 继承但在 publish 中登记 legacy=true，
      下次哈希变化后不再继承。
    """
    old = _load_old_report(report_path)
    old_pub = old.get("publish")
    if not (isinstance(old_pub, dict) and old_pub):
        return report
    old_sha = (old.get("video") or {}).get("sha256", "")
    new_sha = report["video"]["sha256"]
    if old_sha and old_sha != new_sha:
        print(f"[finalize] 视频哈希已变化（旧 {old_sha[:12]}… → 新 {new_sha[:12]}…），"
              "旧版发布回执不继承，需重新发布后回写")
        return report
    if old_sha:
        report["publish"] = old_pub
    else:
        legacy = dict(old_pub)
        legacy["_legacy_without_sha"] = True
        report["publish"] = legacy
    return report


def _rel_to_root(path: str) -> str:
    """登记用的路径（P0-3 改为绝对路径）。

    项目规则（AGENTS.md）与 2026-10-28 方案 P0-3 验收均要求 handoff.md
    登记绝对路径（发布方 Agent 不在项目根目录工作，相对路径曾造成找不到文件）。
    """
    return os.path.abspath(path)


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
        f"- 质量门：配图{'已审' if report.get('quality', {}).get('images_reviewed') else '待审'} / "
        f"片尾{'已查' if report.get('quality', {}).get('tail_frame_checked') else '未查'} / "
        f"混音 {report.get('quality', {}).get('audio_mix_status', 'unknown')}",
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

    # 1) 已有同日自动登记块：只在该日期块内替换 finalize 区（P0-3 修复：
    #    旧实现于整份文件中替换首个 finalize 区，补做旧日登记会覆盖最新日期）
    pattern = rf"### 自动登记（{re.escape(date)}）\n.*?(?=\n### |\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        section = match.group(0)
        if FINALIZE_BEGIN in section:
            # 精细替换：仅该日期块内的 finalize 区
            fin_pattern = rf"{re.escape(FINALIZE_BEGIN)}.*?{re.escape(FINALIZE_END)}"
            new_fin = (FINALIZE_BEGIN
                       + block.split(FINALIZE_BEGIN, 1)[1].split(FINALIZE_END, 1)[0]
                       + FINALIZE_END)
            new_section = re.sub(fin_pattern, lambda _: new_fin, section,
                                 count=1, flags=re.DOTALL)
            if not had_publish_region and PUBLISH_BEGIN not in new_section:
                new_section = new_section.replace(
                    FINALIZE_END,
                    FINALIZE_END + "\n" + PUBLISH_BEGIN + "\n" + PUBLISH_END, 1)
            content = content[:match.start()] + new_section + content[match.end():]
        else:
            content = content[:match.start()] + block.rstrip() + "\n" + content[match.end():]
    else:
        marker = "## 视频登记"
        if marker in content:
            content = content.replace(marker, marker + "\n\n" + block, 1)
        else:
            content += "\n\n## 视频登记\n\n" + block

    content = _archive_handoff_if_oversize(content, handoff_path, date)

    with open(handoff_path, "w", encoding="utf-8") as f:
        f.write(content)


_DATE_BLOCK_RE = re.compile(r"### 自动登记（(\d{4}-\d{2}-\d{2})）\n.*?(?=\n### |\n## |\Z)",
                            re.DOTALL)


def _archive_handoff_if_oversize(content: str, handoff_path: str,
                                 current_date: str) -> str:
    """超过 24 KiB 时把历史日期块归档，保留当前日期与其后最近 2 个日期块。

    归档文件：与 handoff.md 同目录的 handoff-archive-<时间戳>.md。
    只裁剪「自动登记」日期块，不触碰其他人工维护章节；无日期块可裁时不动作。
    """
    if len(content.encode("utf-8")) <= HANDOFF_MAX_BYTES:
        return content
    blocks = list(_DATE_BLOCK_RE.finditer(content))
    if len(blocks) <= 3:
        return content      # 没有可归档的历史块，保持原样（宁可超限不丢数据）
    keep_dates = {current_date}
    # 日期块按文件出现顺序保留最新 2 个（文件内新日期通常在前，但按实际顺序取）
    others = [m.group(1) for m in blocks if m.group(1) != current_date]
    keep_dates.update(others[:2])

    archived = []
    out_parts = []
    pos = 0
    for start, end, text, bdate in ((m.start(), m.end(), m.group(0), m.group(1))
                                    for m in blocks):
        out_parts.append(content[pos:start])
        if bdate in keep_dates:
            out_parts.append(text)
        else:
            archived.append(text)
        pos = end
    out_parts.append(content[pos:])
    if not archived:
        return content
    archive_path = os.path.join(
        os.path.dirname(os.path.abspath(handoff_path)),
        "handoff-archive-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".md",
    )
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write("# handoff 历史归档（超过 24 KiB 自动裁剪，P0-3）\n\n"
                + "\n".join(a.rstrip() for a in archived) + "\n")
    print(f"[finalize] handoff 超限，{len(archived)} 个历史日期块归档 -> {archive_path}")
    return "".join(out_parts)


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
    report = merge_existing_quality(report, report_path)
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
